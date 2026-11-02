#!/bin/bash
set -e
function print_help() {
    helptext=$("${CONDA_EXE}" constructor uninstall --help)
    options=$(awk '/^options:$/ {found=1; next} found' <<<"${helptext}" | grep -Ev '^ *--prefix ')
    cli_args=$(echo "${options}" | sed -e '/^ *-/!d' | awk '{print $1}')
    yes_arg="-y, --yes"
    max_len=$(echo -e "${cli_args}\n${yes_arg}" | awk '{print length}' | sort -n | tail -n 1)
    printf "usage: %s [options]\n\n" "$0"
    printf "options\n\n"
    printf "%s\n" "${options}"
    printf "  %-${max_len}s Skip confirmation dialog.\n" "${yes_arg}"
}

INSTDIR=$(cd "$(dirname "$0")" && pwd)
CONDA_EXE="${INSTDIR}/_conda"
if [[ ! -f "${CONDA_EXE}" ]]; then
    printf "ERROR: Could not find file required for uninstallation: %s.\n" "${CONDA_EXE}"
    exit 1
fi

args=()
confirm_uninstall=true
delete_anaconda_dir=false
while [[ $# -gt 0 ]]; do
    case "$1" in
    -h | --help)
        print_help
        exit 0
        ;;
    -y | --yes)
        confirm_uninstall=false
        shift
        ;;
    --remove-user-data)
        delete_anaconda_dir=true
        args+=("$1")
        shift
        ;;
    *)
        args+=("$1")
        shift
        ;;
    esac
done

if ${confirm_uninstall}; then
    printf "Are you sure you want to remove %s and all of its contents?\n" "${INSTDIR}"
    printf "[no] >>> "
    read -r answer
    answer=$(tr '[:upper:]' '[:lower:]' <<<"${answer}")
    if [[ "${answer}" != "yes" ]] && [[ "${answer}" != "y" ]]; then
        printf "Aborting uninstallation\n"
        exit 2
    fi
fi

# Unset library paths similar to the installation process
if [[ "$(uname)" == "Darwin" ]]; then
    unset DYLD_LIBRARY_PATH DYLD_FALLBACK_LIBRARY_PATH DYLD_INSERT_LIBRARIES DYLD_FRAMEWORK_PATH
else
    unset LD_LIBRARY_PATH LD_PRELOAD LD_AUDIT
fi

# Unset so that conda-standalone does not use a system configuration file
unset CONDARC

echo "Preparing the uninstallation..."
"${CONDA_EXE}" constructor update-bootstrapper >/dev/null 2>&1 || true

"${CONDA_EXE}" constructor uninstall --prefix "${INSTDIR}" "${args[@]}"

# Remove .anaconda after conda uninstall completes, not before.
# The anaconda-auth plugin's keyring check recreates this directory during uninstall.
if ${delete_anaconda_dir}; then
    rm -rf "${HOME}/.anaconda"
fi
