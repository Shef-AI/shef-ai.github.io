"""Read attribution data from installer and write it into a token file.

This module provides functions for reading attribution data embedded in
Anaconda installers across all platforms:

- Windows (.exe): Attribution stored in PE certificate table after `ANACONDA_ATTR` tag
- Linux/macOS (.sh): Attribution exported as `ANACONDA_ATTR` environment variable
- macOS (.pkg): Attribution appended as trailing data after xar archive

This module is designed to be called during the post-install step of
Anaconda installers to extract and save the installer token.
"""

import mmap
import os
import platform
import struct
import sys
from pathlib import Path
from typing import Callable, Dict, Optional
from urllib.parse import parse_qs, unquote

INSTALLER_TOKEN_FILE_NAME = ".installer_token"


# =============================================================================
# Windows PE (.exe) reader - reads from certificate table padding
# =============================================================================


def read_installer_attribution_windows(filepath: Path) -> str:
    """Read attribution data from a signed PE file.

    This function looks for the `ANACONDA_ATTR` tag in the certificate table
    and returns the data that follows it (up to the next null byte or end of space).

    Parameters
    ----------
    filepath: Path
        Path to the installer file

    Returns
    -------
    str
        The attribution data string (URL-encoded query string format)

    Raises
    ------
    RuntimeError:
        When the file is not a valid PE file or does not contain any attribution data.
    ValueError:
        When the PE format is unknown.

    """
    with filepath.open(mode="rb") as file:
        mapped = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            # Get the location of the PE header and the optional header
            if len(mapped) < 0x40:
                raise RuntimeError("File is not a valid PE file: PE header missing.")

            pe_header_offset = struct.unpack("<I", mapped[0x3C:0x40])[0]

            # Validate PE signature
            if mapped[pe_header_offset : pe_header_offset + 4] != b"PE\x00\x00":
                raise RuntimeError("File is not a valid PE file: invalid PE signature.")

            optional_header_offset = pe_header_offset + 24

            # Look up the magic number in the optional header,
            # so we know if we have a 32 or 64-bit executable.
            pe_magic_number = struct.unpack(
                "<H", mapped[optional_header_offset : optional_header_offset + 2]
            )[0]
            if pe_magic_number == 0x10B:
                # 32-bit
                cert_dir_entry_offset = optional_header_offset + 128
            elif pe_magic_number == 0x20B:
                # 64-bit. Certain header fields are wider.
                cert_dir_entry_offset = optional_header_offset + 144
            else:
                raise ValueError(
                    f"Unknown PE format. Magic number: {pe_magic_number:X}"
                )

            # The certificate table offset and length give us the valid range
            # to search through for our attribution data.
            cert_table_offset = struct.unpack(
                "<I", mapped[cert_dir_entry_offset : cert_dir_entry_offset + 4]
            )[0]
            cert_table_size = struct.unpack(
                "<I", mapped[cert_dir_entry_offset + 4 : cert_dir_entry_offset + 8]
            )[0]

            if cert_table_offset == 0 or cert_table_size == 0:
                raise RuntimeError("File is not signed.")

            tag = b"ANACONDA_ATTR"
            tag_index = mapped.find(
                tag, cert_table_offset, cert_table_offset + cert_table_size
            )
            if tag_index == -1:
                raise RuntimeError("Could not find tag `ANACONDA_ATTR` in signature.")

            # Read the data after the tag
            data_start = tag_index + len(tag)
            # Find the end of the reserved space (1024 bytes from tag start)
            max_data_end = tag_index + 1024
            data_end = min(cert_table_offset + cert_table_size, max_data_end)

            # Extract the raw data
            raw_data = mapped[data_start:data_end]

            # Find the first null byte to determine actual data length
            null_index = raw_data.find(b"\x00")
            if null_index != -1:
                raw_data = raw_data[:null_index]
            return raw_data.decode("utf-8")
        finally:
            mapped.close()


# =============================================================================
# Shell script (.sh) reader - reads from environment variable or script parsing
# =============================================================================


def read_installer_attribution_from_env() -> Optional[str]:
    """Read attribution data from the ANACONDA_ATTR environment variable.

    This is the primary method for post-install scripts to access attribution data,
    as the installer exports this variable before running post-install scripts.

    Returns
    -------
    Optional[str]
        Attribution data string if found, None otherwise.

    """
    return os.environ.get("ANACONDA_ATTR")


def read_installer_attribution_from_sh_file(filepath: Path) -> Optional[str]:
    """Read attribution data from a shell script file.

    Looks for an export statement that sets ANACONDA_ATTR environment variable.
    Format: export ANACONDA_ATTR='<data>'

    Parameters
    ----------
    filepath: Path
        Path to the shell script installer

    Returns
    -------
    Optional[str]
        Attribution data string if found, None otherwise.

    """
    try:
        with filepath.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.strip().startswith("export ANACONDA_ATTR="):
                    # Extract the value between quotes (single quotes expected)
                    if "'" in line:
                        parts = line.split("'")
                        if len(parts) >= 2:
                            data = parts[1].strip()
                            if data:
                                return data
                    elif '"' in line:
                        parts = line.split('"')
                        if len(parts) >= 2:
                            data = parts[1].strip()
                            if data:
                                return data
    except Exception:
        pass
    return None


def read_installer_attribution_sh(filepath: Path) -> Optional[str]:
    """Read attribution data from a shell script installer.

    First tries to read from ANACONDA_ATTR environment variable (primary method),
    then falls back to parsing the shell script file.

    Parameters
    ----------
    filepath: Path
        Path to the shell script installer

    Returns
    -------
    Optional[str]
        Attribution data string if found, None otherwise.

    """
    attribution_data = read_installer_attribution_from_env()
    if not attribution_data:
        attribution_data = read_installer_attribution_from_sh_file(filepath)
    return attribution_data


# =============================================================================
# macOS .pkg reader - reads from trailing data after xar archive
# =============================================================================


def read_installer_attribution_pkg(filepath: Path) -> Optional[str]:
    """Read attribution data from a .pkg installer's trailing data.

    The attribution is stored as "ANACONDA_ATTR" marker followed by the data,
    appended after the xar archive. This does not affect code signing,
    notarization, or Gatekeeper validation.

    Parameters
    ----------
    filepath: Path
        Path to the .pkg installer

    Returns
    -------
    Optional[str]
        Attribution data string if found, None otherwise.

    """
    try:
        with filepath.open("rb") as file:
            # Check xar magic
            magic = file.read(4)
            if magic != b"xar!":
                return None

            # Read the entire file to search for marker
            file.seek(0)
            data = file.read()

            tag = b"ANACONDA_ATTR"
            # Search from the end since attribution is in trailing data
            idx = data.rfind(tag)
            if idx == -1:
                return None

            # Extract everything after the marker
            data_start = idx + len(tag)
            if data_start >= len(data):
                return None

            attribution = data[data_start:]

            # Convert to string
            try:
                return attribution.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    return attribution.decode("latin-1")
                except UnicodeDecodeError:
                    return None

    except OSError:
        return None


# =============================================================================
# Platform dispatcher
# =============================================================================

# Map platform to reader function
PLATFORM_READERS: Dict[str, Callable[[Path], Optional[str]]] = {
    "windows": read_installer_attribution_windows,
    "linux": read_installer_attribution_sh,
    "darwin": read_installer_attribution_sh,
}


def read_installer_attribution(
    filepath: Path, platform_name: Optional[str] = None
) -> Optional[str]:
    """Read attribution data from an installer file.

    Automatically detects the platform and file type to use the appropriate
    reader. For .sh files on any platform, uses the shell script reader.
    For .pkg files, uses the pkg reader. For .exe files, uses the Windows
    PE reader.

    Parameters
    ----------
    filepath: Path
        Path to the installer file.
    platform_name: Optional[str]
        Override platform detection. Options: 'windows', 'darwin', 'linux'.
        If not provided, uses the current platform.

    Returns
    -------
    Optional[str]
        Attribution data as string, or None if not found.

    """
    if not filepath.exists():
        return None

    # Determine file type from extension
    suffix = filepath.suffix.lower()

    # .pkg files have their own reader regardless of platform
    if suffix == ".pkg":
        return read_installer_attribution_pkg(filepath)

    # .sh files use shell script reader regardless of platform
    if suffix == ".sh":
        return read_installer_attribution_sh(filepath)

    # For other files, use platform-specific reader
    system_platform = platform_name or platform.system().lower()

    reader = PLATFORM_READERS.get(system_platform)
    if reader is None:
        return None

    try:
        return reader(filepath)
    except Exception:
        return None


# =============================================================================
# Parsing and saving
# =============================================================================


def parse_installer_attribution(attribution_data: str) -> dict:
    """Parse URL-encoded attribution data into a dictionary.

    Parameters
    ----------
    attribution_data: str
        URL-encoded query string with attribution parameters

    Returns
    -------
    dict
        Parsed attribution parameters. Values are unwrapped from
        lists if they contain a single item.

    """
    decoded_attribution_data = unquote(attribution_data)
    parsed_attribution_data = parse_qs(decoded_attribution_data)
    # parse_qs returns values packed in a list
    parsed_attribution_data = {
        k: v[0] if len(v) == 1 else v for k, v in parsed_attribution_data.items()
    }
    return parsed_attribution_data


def save_installer_attribution(
    installer_file: Path,
    installer_token_out_file: Path,
    platform_name: Optional[str] = None,
) -> bool:
    """Save installer attribution data to local .installer_token file.

    Parameters
    ----------
    installer_file: Path
        Path to the installer file to read attribution from.
    installer_token_out_file: Path
        The path to save the .installer_token file.
    platform_name: Optional[str]
        Override platform detection. Options: 'windows', 'darwin', 'linux'.

    Returns
    -------
    bool
        True if the token was saved successfully, False otherwise.

    """
    attribution_data = read_installer_attribution(installer_file, platform_name)
    # Do not write token if attribution data is empty
    if not attribution_data:
        return False
    parsed_attribution_data = parse_installer_attribution(attribution_data)
    installer_token = parsed_attribution_data.get("installer_token")
    if not installer_token:
        raise RuntimeError("No installer_token found in attribution data")
    installer_token_out_file.parent.mkdir(exist_ok=True, parents=True)
    installer_token_out_file.write_text(installer_token)
    return True


# =============================================================================
# CLI
# =============================================================================


def _cli():
    """CLI for extracting installer attribution and saving the token."""
    from argparse import ArgumentParser

    parser = ArgumentParser(
        description=(
            "Reads the attribution data from an installer and writes it into the "
            f"{INSTALLER_TOKEN_FILE_NAME} token file."
        ),
    )
    parser.add_argument(
        "installer_file",
        help="Path to the installer file",
    )
    parser.add_argument(
        "--prefix",
        help="Path to the directory where the installer token will be saved",
        required=True,
    )
    parser.add_argument(
        "--platform",
        choices=["windows", "darwin", "linux"],
        help="Override platform detection",
    )
    args = parser.parse_args()
    installer_file = Path(args.installer_file)
    if not installer_file.is_file():
        print(f"Error: {installer_file} does not exist.", file=sys.stderr)
        sys.exit(1)
    token_file = Path(args.prefix) / INSTALLER_TOKEN_FILE_NAME
    try:
        saved = save_installer_attribution(installer_file, token_file, args.platform)
        if saved:
            print(f"Installer token saved to {token_file}")
        else:
            print("No attribution data found in installer.")
    except RuntimeError as e:
        print(f"Warning: {e}", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    _cli()
