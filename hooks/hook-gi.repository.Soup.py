#-----------------------------------------------------------------------------
# Copyright (c) 2005-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

from PyInstaller.utils.hooks import get_hook_config
from PyInstaller.utils.hooks.gi import GiModuleInfo, collect_glib_translations


def hook(hook_api):
    # Try Soup 3.0 first (used with WebKit2 4.1 on Ubuntu 24.04+), fall back to 2.4
    module_info = GiModuleInfo('Soup', '3.0')
    if not module_info.available:
        module_info = GiModuleInfo('Soup', '2.4')
    if not module_info.available:
        return

    binaries, datas, hiddenimports = module_info.collect_typelib_data()

    lang_list = get_hook_config(hook_api, "gi", "languages")
    datas += collect_glib_translations('libsoup-3.0', lang_list)
    datas += collect_glib_translations('libsoup-2.4', lang_list)

    hook_api.add_datas(datas)
    hook_api.add_binaries(binaries)
    hook_api.add_imports(*hiddenimports)
