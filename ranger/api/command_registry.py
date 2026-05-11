# This file is part of ranger, the console file manager.
# License: GNU GPL version 3, see the file "AUTHORS" for details.

from __future__ import (absolute_import, division, print_function)

import re

from ranger.core.shared import FileManagerAware


_ALIAS_LINE_RE = re.compile(r'(\s+)')


def _get_command_helpers():
    """Lazy import to avoid circular imports."""
    from ranger.api.commands import (
        Command,
        _command_init,
        command_alias_factory,
        command_function_factory,
    )
    return Command, _command_init, command_alias_factory, command_function_factory


class CommandRegistry(FileManagerAware):
    """
    A unified command registry that centralizes command registration,
    lookup, and management.

    This class consolidates the command management functionality that was
    previously scattered across multiple files, providing a single,
    consistent interface for:
    - Registering commands from modules
    - Registering commands from objects (e.g., Actions class methods)
    - Creating command aliases
    - Looking up commands (with optional abbreviation support)
    - Generating command completions
    """

    def __init__(self):
        self._commands = {}

    def __getitem__(self, key):
        return self._commands[key]

    @property
    def commands(self):
        return self._commands

    def register(self, name, command_class):
        """
        Register a command class with the registry.

        Args:
            name: The name of the command
            command_class: The command class to register
        """
        _, _command_init, _, _ = _get_command_helpers()
        self._commands[name] = _command_init(command_class)

    def alias(self, name, full_command):
        """
        Create an alias for an existing command.

        Args:
            name: The name of the new alias
            full_command: The full command that the alias should expand to
        """
        _, _command_init, command_alias_factory, _ = _get_command_helpers()
        cmd_name = full_command.split()[0]
        cmd_cls = self.get_command(cmd_name)
        if cmd_cls is None:
            self.fm.notify('alias failed: No such command: {0}'.format(cmd_name), bad=True)
        else:
            self._commands[name] = _command_init(command_alias_factory(name, cmd_cls, full_command))

    def load_commands_from_module(self, module):
        """
        Load all Command subclasses from a module.

        Args:
            module: The module to load commands from
        """
        Command, _command_init, _, _ = _get_command_helpers()
        for var in vars(module).values():
            try:
                if issubclass(var, Command) and var != Command:
                    self._commands[var.get_name()] = _command_init(var)
            except TypeError:
                pass

    def load_commands_from_object(self, obj, filtr):
        """
        Load callable attributes from an object as commands.

        Args:
            obj: The object to load commands from
            filtr: A set of attribute names to include
        """
        _, _command_init, _, command_function_factory = _get_command_helpers()
        for attribute_name in dir(obj):
            if attribute_name[0] == '_' or attribute_name not in filtr:
                continue
            attribute = getattr(obj, attribute_name)
            if hasattr(attribute, '__call__'):
                self._commands[attribute_name] = _command_init(command_function_factory(attribute))

    def get_command(self, name, abbrev=False):
        """
        Look up a command by name.

        Args:
            name: The command name to look up
            abbrev: If True, allow abbreviated command names

        Returns:
            The command class if found, None otherwise

        Raises:
            KeyError: If abbrev=True and no matching command is found
            ValueError: If abbrev=True and multiple commands match
        """
        if abbrev:
            lst = [cls for cmd, cls in self._commands.items()
                   if cls.allow_abbrev and cmd.startswith(name) or cmd == name]
            if not lst:
                raise KeyError
            if len(lst) == 1:
                return lst[0]
            if self._commands[name] in lst:
                return self._commands[name]
            raise ValueError("Ambiguous command")

        try:
            return self._commands[name]
        except KeyError:
            return None

    def command_generator(self, start):
        """
        Generate command names that start with the given prefix.

        Args:
            start: The prefix to match

        Returns:
            A sorted list of matching command names with a trailing space
        """
        return sorted(cmd + ' ' for cmd in self._commands if cmd.startswith(start))
