from conda import plugins


def pre_command_patcher(command):
    try:
        from . import patch  # noqa

        patch.main(plugin=True, command=command)
    except Exception as exc:  # pragma: nocover
        print("Error loading anaconda-anon-usage:", exc)


class AlwaysContains:
    def __contains__(self, item):
        return True


@plugins.hookimpl
def conda_pre_commands():
    yield plugins.types.CondaPreCommand(
        name="anaconda-anon-usage",
        action=pre_command_patcher,
        # This ensures the plugin is run no matter what
        # conda command is being called
        run_for=AlwaysContains(),
    )
