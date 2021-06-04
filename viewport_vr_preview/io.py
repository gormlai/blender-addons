# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8 compliant>

# -----------------------------------------------------------------------------
# Export Functions

__all__ = (
    "actionconfig_export_as_data",
    "actionconfig_import_from_data",
    "actionconfig_init_from_data",
    "actionmap_init_from_data",
)


def indent(levels):
    return levels * " "


def round_float_32(f):
    from struct import pack, unpack
    return unpack("f", pack("f", f))[0]


def repr_f32(f):
    f_round = round_float_32(f)
    f_str = repr(f)
    f_str_frac = f_str.partition(".")[2]
    if not f_str_frac:
        return f_str
    for i in range(1, len(f_str_frac)):
        f_test = round(f, i)
        f_test_round = round_float_32(f_test)
        if f_test_round == f_round:
            return "%.*f" % (i, f_test)
    return f_str


def am_args_as_data(am):
    s = [
        f"\"profile\": '{am.profile}'",
    ]

    return "{" + ", ".join(s) + "}"


def am_data_from_args(am, args):    
    am.profile = args["profile"]


def ami_args_as_data(ami):
    s = [
        f"\"type\": '{ami.type}'",
        f"\"user_path0\": '{ami.user_path0}'",
        f"\"component_path0\": '{ami.component_path0}'",
        f"\"user_path1\": '{ami.user_path1}'",
        f"\"component_path1\": '{ami.component_path1}'",
    ]

    if ami.type == 'BUTTON' or ami.type == 'AXIS':
        s.append(f"\"threshold\": '{ami.threshold}'")
        s.append(f"\"op\": '{ami.op}'")
        s.append(f"\"op_flag\": '{ami.op_flag}'")
    elif ami.type == 'POSE':
        s.append(f"\"pose_is_controller\": '{ami.pose_is_controller}'")
        s.append(f"\"pose_location\": '{ami.pose_location.x, ami.pose_location.y, ami.pose_location.z}'")
        s.append(f"\"pose_rotation\": '{ami.pose_rotation.x, ami.pose_rotation.y, ami.pose_rotation.z}'")
    elif ami.type == 'HAPTIC':
        s.append(f"\"haptic_duration\": '{ami.haptic_duration}'")
        s.append(f"\"haptic_frequency\": '{ami.haptic_frequency}'")
        s.append(f"\"haptic_amplitude\": '{ami.haptic_amplitude}'")


    return "{" + ", ".join(s) + "}"


def ami_data_from_args(ami, args):    
    ami.type = args["type"]
    ami.user_path0 = args["user_path0"]
    ami.component_path0 = args["component_path0"]
    ami.user_path1 = args["user_path1"]
    ami.component_path1 = args["component_path1"]
    
    if ami.type == 'BUTTON' or ami.type == 'AXIS':
        ami.threshold = float(args["threshold"])
        ami.op = args["op"]
        ami.op_flag = args["op_flag"]
    elif ami.type == 'POSE':
        ami.pose_is_controller = bool(args["pose_is_controller"])
        l = args["pose_location"].strip(')(').split(', ')
        ami.pose_location.x = float(l[0])
        ami.pose_location.y = float(l[1])
        ami.pose_location.z = float(l[2])
        l = args["pose_rotation"].strip(')(').split(', ')
        ami.pose_rotation.x = float(l[0])
        ami.pose_rotation.y = float(l[1])
        ami.pose_rotation.z = float(l[2])
    elif ami.type == 'HAPTIC':
        ami.haptic_duration = float(args["haptic_duration"])
        ami.haptic_frequency = float(args["haptic_frequency"])
        ami.haptic_amplitude = float(args["haptic_amplitude"])


def _ami_properties_to_lines_recursive(level, properties, lines):
    from bpy.types import OperatorProperties

    def string_value(value):
        if isinstance(value, (str, bool, int, set)):
            return repr(value)
        elif isinstance(value, float):
            return repr_f32(value)
        elif getattr(value, '__len__', False):
            return repr(tuple(value))
        raise Exception(f"Export action configuration: can't write {value!r}")

    for pname in properties.bl_rna.properties.keys():
        if pname != "rna_type":
            value = getattr(properties, pname)
            if isinstance(value, OperatorProperties):
                lines_test = []
                _ami_properties_to_lines_recursive(level + 2, value, lines_test)
                if lines_test:
                    lines.append(f"(")
                    lines.append(f"\"{pname}\",\n")
                    lines.append(f"{indent(level + 3)}" "[")
                    lines.extend(lines_test)
                    lines.append("],\n")
                    lines.append(f"{indent(level + 3)}" "),\n" f"{indent(level + 2)}")
                del lines_test
            elif properties.is_property_set(pname):
                value = string_value(value)
                lines.append((f"(\"{pname}\", {value:s}),\n" f"{indent(level + 2)}"))


def _ami_properties_to_lines(level, ami_props, lines):
    if ami_props is None:
        return

    lines_test = [f"\"op_properties\":\n" f"{indent(level + 1)}" "["]
    _ami_properties_to_lines_recursive(level, ami_props, lines_test)
    if len(lines_test) > 1:
        lines_test.append("],\n")
        lines.extend(lines_test)


def _ami_attrs_or_none(level, ami):
    lines = []
    _ami_properties_to_lines(level + 1, ami.op_properties, lines)
    if not lines:
        return None
    return "".join(lines)


def actionconfig_export_as_data(ac, filepath, *, all_actionmaps=True, sort=False):
    export_actionmaps = []

    for am in ac.actionmaps:
        if all_actionmaps or am.is_user_modified:
            export_actionmaps.append(am)

    if sort:
        export_actionmaps.sort(key=lambda k: k.name)

    with open(filepath, "w", encoding="utf-8") as fh:
        fw = fh.write

        # Use the file version since it includes the sub-version
        # which we can bump multiple times between releases.
        from bpy.app import version_file
        fw(f"actionconfig_version = {version_file!r}\n")
        del version_file

        fw("actionconfig_data = \\\n[")

        for am in export_actionmaps:
            fw("(")
            fw(f"\"{am.name:s}\",\n")
            fw(f"{indent(2)}")
            am_args = am_args_as_data(am)
            fw(am_args)
            fw(",\n")
            fw(f"{indent(2)}" "{")
            fw(f"\"items\":\n")
            fw(f"{indent(3)}[")
            for ami in am.actionmap_items:
                fw(f"(")
                ami_args = ami_args_as_data(ami)
                ami_data = _ami_attrs_or_none(4, ami)
                fw(f"\"{ami.name:s}\"")
                if ami_data is None:
                    fw(f", ")
                else:
                    fw(",\n" f"{indent(5)}")

                fw(ami_args)
                if ami_data is None:
                    fw(", None),\n")
                else:
                    fw(",\n")
                    fw(f"{indent(5)}" "{")
                    fw(ami_data)
                    fw(f"{indent(6)}")
                    fw("},\n" f"{indent(5)}")
                    fw("),\n")
                fw(f"{indent(4)}")
            fw("],\n" f"{indent(3)}")
            fw("},\n" f"{indent(2)}")
            fw("),\n" f"{indent(1)}")

        fw("]\n")
        fw("\n\n")
        fw("if __name__ == \"__main__\":\n")

        # We could remove this in the future, as loading new action-maps in older Blender versions
        # makes less and less sense as Blender changes.
        fw("    # Only add keywords that are supported.\n")
        fw("    from bpy.app import version as blender_version\n")
        fw("    keywords = {}\n")
        fw("    if blender_version >= (3, 0, 0):\n")
        fw("        keywords[\"actionconfig_version\"] = actionconfig_version\n")

        fw("    import os\n")
        fw("    from viewport_vr_preview.io import actionconfig_import_from_data\n")
        fw("    actionconfig_import_from_data(\n")
        fw("        os.path.splitext(os.path.basename(__file__))[0],\n")
        fw("        actionconfig_data,\n")
        fw("        **keywords,\n")
        fw("    )\n")


# -----------------------------------------------------------------------------
# Import Functions

def _ami_props_setattr(ami_props, attr, value):
    if type(value) is list:
        ami_subprop = getattr(ami_props, attr)
        for subattr, subvalue in value:
            _ami_props_setattr(ami_subprop, subattr, subvalue)
        return

    try:
        setattr(ami_props, attr, value)
    except AttributeError:
        print(f"Warning: property '{attr}' not found in actionmap item '{ami_props.__class__.__name__}'")
    except Exception as ex:
        print(f"Warning: {ex!r}")


def actionmap_init_from_data(am, am_items):
    new_fn = getattr(am.actionmap_items, "new")
    for (ami_name, ami_args, ami_data) in am_items:
        ami = new_fn(ami_name, True)
        ami_data_from_args(ami, ami_args)
        if ami_data is not None:
            ami_props_data = ami_data.get("op_properties", None)
            if ami_props_data is not None:
                ami_props = ami.op_properties
                assert type(ami_props_data) is list
                for attr, value in ami_props_data:
                    _ami_props_setattr(ami_props, attr, value)


def actionconfig_init_from_data(ac, actionconfig_data, actionconfig_version):
    # Load data in the format defined above.
    #
    # Runs at load time, keep this fast!
    if actionconfig_version is not None:
        from .versioning import actionconfig_update
        actionconfig_data = actionconfig_update(actionconfig_data, actionconfig_version)
    
    for (am_name, am_args, am_content) in actionconfig_data:
        am = ac.actionmaps.new(am_name, True)
        am_data_from_args(am, am_args)
        am_items = am_content["items"]
        # Check here instead of inside 'actionmap_init_from_data'
        # because we want to allow both tuple & list types in that case.
        #
        # For full actionmaps, ensure these are always lists to allow for extending them
        # in a generic way that doesn't have to check for the type each time.
        assert type(am_items) is list
        actionmap_init_from_data(am, am_items)


def actionconfig_import_from_data(name, actionconfig_data, *, actionconfig_version=(0, 0, 0)):
    # Load data in the format defined above.
    #
    # Runs at load time, keep this fast!
    import bpy
    ac = bpy.context.window_manager.xr_session_settings.actionconfigs.new(name)
    actionconfig_init_from_data(ac, actionconfig_data, actionconfig_version)
    return ac