import bpy.props

# Nico: The __init__.py only designed to register and unregister ,so as a simple control for the whole plugin,
# keep it clean and don't add too many code,code should be in other files and import it here.
# we use .utils instead of utils because blender can't locate where utils is
# Blender can only locate panel.py only when you add a . before it.

from .mmt_panel.panel_ui import *
from .mmt_rightclick_menu.mesh_operator import *
from .mmt_animation.animation_operator import *


bl_info = {
    "name": "DBMT-Blender-Plugin",
    "description": "DBMT's Blender 3.6LTS Plugin",
    "blender": (3, 6, 0),
    "version": (1, 0, 0, 3),
    "location": "View3D",
    "category": "Generic"
}


register_classes = (
    # migoto
    MMTPathProperties,
    MMTPathOperator,
    MMTPanel,

    # 3Dmigoto ib和vb格式导入导出
    Import3DMigotoRaw,
    Export3DMigoto,

    # MMT的一键快速导入导出
    MMTImportAllVbModel,
    MMTExportAllIBVBModel,

    # mesh_operator 右键菜单栏
    RemoveUnusedVertexGroupOperator,
    MergeVertexGroupsWithSameNumber,
    FillVertexGroupGaps,
    AddBoneFromVertexGroup,
    RemoveNotNumberVertexGroup,
    ConvertToFragmentOperator,
    MMTDeleteLoose,
    MMTResetRotation,
    MigotoRightClickMenu,
    MMTCancelAutoSmooth,
    MMTShowIndexedVertices,
    MMTSetAutoSmooth89,
    SplitMeshByCommonVertexGroup,



    # MMD类型动画Mod支持
    MMDModIniGenerator
)


def register():
    for cls in register_classes:
        # make_annotations(cls)
        bpy.utils.register_class(cls)

    # 新建一个属性用来专门装MMT的路径
    bpy.types.Scene.mmt_props = bpy.props.PointerProperty(type=MMTPathProperties)
    # mesh_operator
    bpy.types.VIEW3D_MT_object_context_menu.append(menu_func_migoto_right_click)

    # 在Blender退出前保存选择的MMT的路径
    bpy.app.handlers.depsgraph_update_post.append(save_mmt_path)

    # MMT数值保存的变量
    bpy.types.Scene.mmt_mmd_animation_mod_start_frame = bpy.props.IntProperty(name="Start Frame")
    bpy.types.Scene.mmt_mmd_animation_mod_end_frame = bpy.props.IntProperty(name="End Frame")
    bpy.types.Scene.mmt_mmd_animation_mod_play_speed = bpy.props.FloatProperty(name="Play Speed")

    
def unregister():
    for cls in reversed(register_classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.mmt_props

    # mesh_operator
    bpy.types.VIEW3D_MT_object_context_menu.remove(menu_func_migoto_right_click)

    # 退出注册时删除MMT的MMD变量
    del bpy.types.Scene.mmt_mmd_animation_mod_start_frame
    del bpy.types.Scene.mmt_mmd_animation_mod_end_frame
    del bpy.types.Scene.mmt_mmd_animation_mod_play_speed


