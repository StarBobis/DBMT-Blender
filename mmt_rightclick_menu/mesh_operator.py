# Nico: 此文件定义右键菜单的功能类。
# 所有操作都要加上bl_options = {'UNDO'}，这样可以支持Ctrl + Z撤销。
from .mesh_functions import *


class RemoveUnusedVertexGroupOperator(bpy.types.Operator):
    bl_idname = "object.remove_unused_vertex_group"
    bl_label = "移除未使用的空顶点组"
    bl_options = {'UNDO'}

    def execute(self, context):
        return remove_unused_vertex_group(self, context)


class MergeVertexGroupsWithSameNumber(bpy.types.Operator):
    bl_idname = "object.merge_vertex_group_with_same_number"
    bl_label = "合并具有相同数字前缀名称的顶点组"
    bl_options = {'UNDO'}
    
    def execute(self, context):
        return merge_vertex_group_with_same_number(self, context)


class FillVertexGroupGaps(bpy.types.Operator):
    bl_idname = "object.fill_vertex_group_gaps"
    bl_label = "填充数字顶点组的间隙"
    bl_options = {'UNDO'}
    
    def execute(self, context):
        return fill_vertex_group_gaps(self, context)


class AddBoneFromVertexGroup(bpy.types.Operator):
    bl_idname = "object.add_bone_from_vertex_group"
    bl_label = "根据顶点组自动生成骨骼"
    bl_options = {'UNDO'}
    
    def execute(self, context):
        return add_bone_from_vertex_group(self, context)


class RemoveNotNumberVertexGroup(bpy.types.Operator):
    bl_idname = "object.remove_not_number_vertex_group"
    bl_label = "移除非数字名称的顶点组"
    bl_options = {'UNDO'}
    
    def execute(self, context):
        return remove_not_number_vertex_group(self, context)


class ConvertToFragmentOperator(bpy.types.Operator):
    bl_idname = "object.convert_to_fragment"
    bl_label = "转换为一个3Dmigoto碎片用于合并"
    bl_options = {'UNDO'}
    
    def execute(self, context):
        return convert_to_fragment(self, context)


class MMTDeleteLoose(bpy.types.Operator):
    bl_idname = "object.mmt_delete_loose"
    bl_label = "删除物体的松散点"
    bl_options = {'UNDO'}
    
    def execute(self, context):
        return delete_loose(self, context)


class MMTResetRotation(bpy.types.Operator):
    bl_idname = "object.mmt_reset_rotation"
    bl_label = "重置x,y,z的旋转角度为0 (UE Model)"
    bl_options = {'UNDO'}
    
    def execute(self, context):
        return mmt_reset_rotation(self, context)


class MMTCancelAutoSmooth(bpy.types.Operator):
    bl_idname = "object.mmt_cancel_auto_smooth"
    bl_label = "取消自动平滑 (UE Model)"
    bl_options = {'UNDO'}
    
    def execute(self, context):
        return mmt_cancel_auto_smooth(self, context)


class MMTSetAutoSmooth89(bpy.types.Operator):
    bl_idname = "object.mmt_set_auto_smooth_89"
    bl_label = "设置Normal的自动平滑为89° (Unity)"
    bl_options = {'UNDO'}
    
    def execute(self, context):
        return mmt_set_auto_smooth_89(self, context)


class MMTShowIndexedVertices(bpy.types.Operator):
    bl_idname = "object.mmt_show_indexed_vertices"
    bl_label = "展示Indexed Vertices和Indexes Number"
    bl_options = {'UNDO'}
    
    def execute(self, context):
        return show_indexed_vertices(self, context)


class SplitMeshByCommonVertexGroup(bpy.types.Operator):
    bl_idname = "object.split_mesh_by_common_vertex_group"
    bl_label = "根据相同的顶点组分割物体"
    bl_options = {'UNDO'}
    
    def execute(self, context):
        return split_mesh_by_common_vertex_group(self, context)

 
# -----------------------------------这个属于右键菜单注册，单独的函数要往上面放---------------------------------------
class MigotoRightClickMenu(bpy.types.Menu):
    bl_idname = "VIEW3D_MT_object_3Dmigoto"
    bl_label = "3Dmigoto"
    bl_options = {'UNDO'}
    
    def draw(self, context):
        layout = self.layout
        # layout.operator可以直接用 [类名.bl_idname] 这样就不用再写一次常量了，方便管理
        layout.operator(RemoveUnusedVertexGroupOperator.bl_idname)
        layout.operator(MergeVertexGroupsWithSameNumber.bl_idname)
        layout.operator(FillVertexGroupGaps.bl_idname)
        layout.operator(AddBoneFromVertexGroup.bl_idname)
        layout.operator(RemoveNotNumberVertexGroup.bl_idname)
        layout.operator(ConvertToFragmentOperator.bl_idname)
        layout.operator(MMTDeleteLoose.bl_idname)
        layout.operator(MMTResetRotation.bl_idname)
        layout.operator(MMTCancelAutoSmooth.bl_idname)
        layout.operator(MMTSetAutoSmooth89.bl_idname)
        layout.operator(MMTShowIndexedVertices.bl_idname)
        layout.operator(SplitMeshByCommonVertexGroup.bl_idname)


# 定义菜单项的注册函数
def menu_func_migoto_right_click(self, context):
    self.layout.menu(MigotoRightClickMenu.bl_idname)
