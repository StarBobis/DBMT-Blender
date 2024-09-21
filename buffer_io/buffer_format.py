'''
写给未来的MMT设计：

1.旧的3Dmigoto的ib和vb格式无法把形态键Buffer数据一起一键导入到Blender中
以及后续常用的BoneMatrix技术，PositionMatrix技术的文件，也无法直观集成进来。

2.每次从FrameAnalysis文件夹中提取后都要把分离的Buffer文件转换成.ib .vb .fmt文件来导入到Blender中
每次导出之后都要进行毫无意义的把ib vb fmt文件拆分为buffer文件

这一个融合和分割，岂不是脱了裤子放屁多此一举。

所以能不能跳过这个融合和分割的过程？？为什么一定要使用DrakStarSword原本的设计呢，很明显对于游戏Mod制作来说
如果Blender插件能直接对Buffer进行导入和导出，那么就能在提取和生成二创模型时减少这个额外的分割工作
并且这样也能更加直观的使用010Editor看到每个Buffer中的内容，也更方便直接性的Buffer操作。

就像MMT刚开始使用类似的GIMI的收集逻辑，从txt里进行收集一样，完全被前人错误的思路给带偏了，现在Blender插件的设计同样如此，前人的设计同样存在问题。

所以要设计一种新的数据格式，目前有两种思路：
1.设计一种.3dm格式把所有数据都装进去，就不需要.ib .vb .fmt三种不同的格式了。
（感觉没必要，不是很好维护，除非生成的Mod也用这种格式，但是那样就要重构3Dmigoto了，不值得，而且不利于其它人进行二次开发，还需要一个额外的文件格式解析器的步骤，不够直观）

2.设计一个新的 format.json，这样Blender插件读取这个json文件来决定哪些Buffer怎样导入到Blender中进行显示。

所以最终采用新的format.json + 其它Buffer文件的形式来描述一个模型的文件夹

所以现有的Blender插件设计基本上要完全舍弃并重新设计了，设计思路可以参考WWMI，WWMI在这方面做的还不错。

但是如何保证兼容性问题，使得其它人导入的.ib .vb .fmt格式，以及-ib.txt 和-vb0.txt格式的模型也能够支持呢？
这一点我觉得只要搞定从模型到写出文件的解析步骤即可，对于.ib .vb以及.txt格式的支持应该安装其它的插件来提供支持，比如使用XXMI等插件？

但是如果这样设计的话，整个MMT的架构就完全改变了，现有的MMT逻辑以及Blender插件逻辑都得重写
不过由于D3D11以及后续普遍使用的D3D12也会普遍使用Buffer格式，所以设计一种新的通用Buffer格式是完全值得的。

主要的问题在于3Dmigoto真的值得嘛？它的使用范围实在是太小，只有数个游戏支持GPU-PreSkinning，不过可以预见未来的游戏应该都会支持GPU-PreSkinning。
而且未来一定会出现通用的GPU-PreSkinning的骨骼融合框架以及形态键框架以及ComputeShader重算骨骼姿态框架等等。
在设计时应该考虑到未来对于其它支持Buffer替换的工具的格式支持，所以基于Buffer和json描述文件的设计是完全可行且向后兼容的。

所以就这么决定了，后续进行格式改变，朝着更通用兼容的方向进行开发：面向未来的程序设计 。。。。
这次决定也许在短期内看不到效果，不过3到5年内，当GPU算力突破，当DX12全面普及，当基于ReShade架构的DX12Buffer Mod工具面世时，MMT现在繁琐的准备和重构工作就是值得的。
决定每个月拿出1到2天进行更新，改为长期技术开发，赌未来的GPU确实可以做到我现在推测的能力。
'''

'''
TODO 在重构完成MMT的导入导出后，删掉上面那一大段话。
'''


import math
import bpy
import struct
import itertools
import re
import bmesh


# This used to catch any exception in run time and raise it to blender output console.
class Fatal(Exception):
    pass



import math
import bpy
import struct
import itertools
import re
import bmesh

def extract_drawindexed_values(ini_file):
    object_data = []
    with open(ini_file, 'r') as file:
        lines = file.readlines()
    
    current_component = None
    component_sums = {}
    
    for line in lines:
        line = line.strip()
        
        if line.startswith('; Draw Component'):
            component_number = extract_component_number(line)
            if component_number is not None:
                current_component = component_number
                if current_component not in component_sums:
                    component_sums[current_component] = (0, None)
        
        if line.startswith('drawindexed'):
            values = re.findall(r'\d+', line)
            if len(values) >= 2:
                value1 = int(values[0])
                value2 = int(values[1])
                if current_component is not None:
                    current_sum, existing_second_value = component_sums[current_component]
                    component_sums[current_component] = (current_sum + value1, existing_second_value if existing_second_value is not None else value2)
    
    for component_number, (sum_value, second_value) in component_sums.items():
        if second_value is not None:
            object_data.append((sum_value, second_value))
    
    return object_data

def extract_component_number(line):
    # Find the part after "; Draw Component"
    match = re.search(r'; Draw Component\s+(\d+)', line)
    if match:
        return int(match.group(1))
    return None

def read_position_buffer(file_path):
    vertices = []
    with open(file_path, 'rb') as f:
        while chunk := f.read(12):  # DXGI_FORMAT_R32G32B32_FLOAT uses 12 bytes per vertex
            x, y, z = struct.unpack('<3f', chunk)
            vertices.append((x, y, z))
    return vertices

def read_index_buffer(file_path):
    indices = []
    with open(file_path, 'rb') as f:
        while chunk := f.read(4):  # Assuming indices are packed as 4 bytes each
            index = struct.unpack('<I', chunk)[0]
            indices.append(index)
    return indices

def read_vector_buffer(file_path):
    tangents = []
    normals = []
    with open(file_path, 'rb') as f:
        while chunk := f.read(8):  # 8 bytes per record for tangents and normals
            if len(chunk) == 8:
                # Extract Tangent (4 bytes for x, y, z, w)
                tx, ty, tz, tw = struct.unpack('<4b', chunk[0:4])
                tangents.append((tx / 127.0, ty / 127.0, tz / 127.0, tw / 127.0))
                
                # Extract Normal (4 bytes for x, y, z, w)
                nx, ny, nz, nw = struct.unpack('<4b', chunk[4:8])
                normals.append((nx / 127.0, ny / 127.0, nz / 127.0, nw / 127.0))
    return tangents, normals

def read_texcoord_buffer(file_path):
    texcoords0 = []
    texcoords1 = []
    texcoords2 = []
    color1 = []
    with open(file_path, 'rb') as f:
        while chunk := f.read(16):  # 16 bytes per record
            if len(chunk) == 16:
                u0, v0 = struct.unpack('<2e', chunk[0:4])
                texcoords0.append((u0, v0))               
                # Extract Color1 (4 bytes for r and g)
                r1, g1 = struct.unpack('<2H', chunk[4:8])
                color1.append((r1 / 65535.0, g1 / 65535.0, 0.0, 0.0))  # Use normalized value
                u1, v1 = struct.unpack('<2e', chunk[8:12])
                texcoords1.append((u1, v1))
                u2, v2 = struct.unpack('<2e', chunk[12:16])
                texcoords2.append((u2, v2))
    
    return texcoords0, texcoords1, texcoords2, color1

def read_color_buffer(file_path):
    color0 = []
    with open(file_path, 'rb') as f:
        while chunk := f.read(4):  # DXGI_FORMAT_R8G8B8A8_UNORM uses 4 bytes per color
            r, g, b, a = struct.unpack('<4B', chunk)
            color0.append((r / 255.0, g / 255.0, b / 255.0, a / 255.0))
    return color0

def read_blend_buffer(file_path):
    blend_indices = []
    blend_weights = []
    with open(file_path, 'rb') as f:
        while chunk := f.read(8):  # 8 bytes per record (4 bytes for indices + 4 bytes for weights)
            if len(chunk) == 8:
                indices = struct.unpack('<4B', chunk[:4])  # 4 bytes for blend indices
                weights = struct.unpack('<4B', chunk[4:])  # 4 bytes for blend weights
                blend_indices.append(indices)
                blend_weights.append(weights)
    blend_weights = normalize_weights(blend_weights)
    return blend_indices, blend_weights

def normalize_weights(weights):
    normalized_weights = []
    for weight_set in weights:
        total_weight = sum(weight_set)
        if total_weight > 0:
            normalized_weights.append(tuple(w / total_weight for w in weight_set))
        else:
            normalized_weights.append(weight_set)  # Avoid division by zero
    return normalized_weights

def read_shape_key_offset(file_path):
    with open(file_path, 'rb') as file:
        data = file.read()
    num_integers = len(data) // 4
    format_string = '<' + 'I' * num_integers
    unpacked_data = struct.unpack(format_string, data)
    
    if len(unpacked_data) > 1:
        unique_data = []
        seen = {}
        for value in reversed(unpacked_data):
            if value not in seen:
                seen[value] = 1
                unique_data.append(value)
            elif seen[value] < 2:
                seen[value] += 1
                unique_data.append(value)
        unique_data.reverse()
        
        unpacked_data = unique_data
    
    return unpacked_data

def read_shape_key_vertex_id(file_path):
    with open(file_path, 'rb') as file:
        data = file.read()
    num_ids = len(data) // 4
    format_string = '<' + 'I' * num_ids
    return struct.unpack(format_string, data)
def read_shape_key_vertex_offset(file_path):
    with open(file_path, 'rb') as file:
        data = file.read()
    num_offsets = len(data) // 2
    format_string = '<' + 'e' * num_offsets
    offsets = struct.unpack(format_string, data)
    cleaned_offsets = []
    for i in range(0, len(offsets), 3):
        triplet = offsets[i:i+3]
        if triplet != (0.0, 0.0, 0.0):
            cleaned_offsets.extend(triplet)

    return cleaned_offsets

def import_uv_layers(mesh, texcoords):
    uv_layers_data = [
        ("TEXCOORD.xy", texcoords[0]),  # TexCoord0
        ("TEXCOORD1.xy", texcoords[1]),  # TexCoord1
        ("TEXCOORD2.xy", texcoords[2])   # TexCoord2
    ]

    for uv_name, uv_data in uv_layers_data:
        if uv_data:
            uv_layer = mesh.uv_layers.new(name=uv_name)
            for poly in mesh.polygons:
                for loop_index in poly.loop_indices:
                    loop = mesh.loops[loop_index]
                    loop_vertex_index = loop.vertex_index

                    if loop_vertex_index < len(uv_data):
                        uv = uv_data[loop_vertex_index]
                        uv_layer.data[loop_index].uv = (uv[0], 1.0 - uv[1])  # Flip V if necessary
                    else:
                        uv_layer.data[loop_index].uv = (0.0, 0.0)

            print(f"UV Layer '{uv_name}' imported successfully.")

def import_vertex_groups(mesh, obj, blend_indices, blend_weights, component=None):
    if len(blend_indices) != len(blend_weights):
        raise ValueError("Mismatch between blend_indices and blend_weights lengths")
    
    connected_vertex_ids = set()
    for poly in mesh.polygons:
        connected_vertex_ids.update(poly.vertices)
    
    connected_blend_indices = set()
    for vertex_index, indices in enumerate(blend_indices):
        if vertex_index in connected_vertex_ids:
            connected_blend_indices.update(indices)
    if component is None:
        num_vertex_groups = max(connected_blend_indices) + 1 if connected_blend_indices else 0
    else:
        num_vertex_groups = max(component.vg_map[i] for i in connected_blend_indices) + 1 if connected_blend_indices else 0
        vg_map = list(map(int, component.vg_map.values()))
    
    vertex_groups = [obj.vertex_groups.new(name=str(i)) for i in range(num_vertex_groups)]
    
    if component is None:
        group_map = {i: vertex_groups[i] for i in connected_blend_indices}
    else:
        group_map = {i: vertex_groups[vg_map[i]] for i in connected_blend_indices}
    
    vertex_weight_map = {v.index: [] for v in mesh.vertices}
    for vertex_index, indices in enumerate(blend_indices):
        weights = blend_weights[vertex_index]
        if vertex_index in connected_vertex_ids and vertex_index in vertex_weight_map:
            for idx, weight in zip(indices, weights):
                if weight > 0.0:
                    vertex_weight_map[vertex_index].append((idx, weight))
    for vertex in mesh.vertices:
        if vertex.index in vertex_weight_map and vertex.index in connected_vertex_ids:
            for idx, weight in vertex_weight_map[vertex.index]:
                group_map[idx].add([vertex.index], weight, 'REPLACE')
    for vg in obj.vertex_groups:
        num_vertices = sum(1 for v in mesh.vertices if vertex_weight_map.get(v.index, []))
        print(f"Vertex Group '{vg.name}' has {num_vertices} vertices assigned.")


def apply_normals(obj, mesh, normals):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='OBJECT')
    if len(normals) != len(mesh.vertices):
        raise ValueError("Number of normals must match the number of vertices.")
    mesh.normals_split_custom_set_from_vertices([normal[:3] for normal in normals])
    mesh.update()
    
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    fmesh = bmesh.from_edit_mesh(obj.data)
    for face in fmesh.faces:
        face.normal_flip()
    bmesh.update_edit_mesh(obj.data)
    bpy.ops.object.mode_set(mode='OBJECT')
    obj.data.update()
    
    mesh.calc_normals_split()
    mesh.update()
    
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.faces_shade_smooth()
    bpy.ops.object.mode_set(mode='OBJECT')
    
    obj.data.update()

def apply_tangents(mesh, tangents):
    if len(tangents) != len(mesh.vertices):
        raise ValueError("Number of tangents must match the number of vertices.")
    if not mesh.uv_layers:
        mesh.uv_layers.new(name="TANGENT")
    mesh.update()

def import_shapekeys(obj, shapekey_offsets, shapekey_vertex_ids, shapekey_vertex_offsets, scale_factor=1.0):
    if len(shapekey_offsets) == 0:
        return

    # Ensure the object is in object mode
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='OBJECT')

    # Get the mesh data
    mesh = obj.data
    vertices = mesh.vertices
    polygons = mesh.polygons

    # Create a set of vertex indices that are part of the mesh (linked to any polygon)
    existing_vertex_ids = set()
    for poly in polygons:
        existing_vertex_ids.update(poly.vertices)

    # Import shapekeys
    num_shapekeys = len(shapekey_offsets)
    basis_shapekey_added = False

    for i in range(num_shapekeys):
        start_offset = shapekey_offsets[i]
        end_offset = shapekey_offsets[i + 1] if i + 1 < num_shapekeys else len(shapekey_vertex_ids)
        
        # Check if there are any valid vertices for this shapekey
        has_valid_vertices = any(vertex_id in existing_vertex_ids for vertex_id in shapekey_vertex_ids[start_offset:end_offset])
        
        if not has_valid_vertices:
            continue

        # Add the basis shapekey if it hasn't been added yet
        if not basis_shapekey_added:
            basis_shapekey = obj.shape_key_add(name='Basis')
            basis_shapekey.interpolation = 'KEY_LINEAR'
            obj.data.shape_keys.use_relative = True
            basis_shapekey_added = True
        
        # Add new shapekey
        shapekey = obj.shape_key_add(name=f'Deform {i}')
        shapekey.interpolation = 'KEY_LINEAR'

        # Apply shapekey vertex position offsets to each indexed vertex
        for j in range(start_offset, end_offset):
            vertex_id = shapekey_vertex_ids[j]
            index = j * 3
            if index + 3 <= len(shapekey_vertex_offsets):  # Ensure indices are within bounds
                position_offset = shapekey_vertex_offsets[index:index + 3]
                
                # Scale the offsets
                position_offset = [scale_factor * offset for offset in position_offset]
                if vertex_id in existing_vertex_ids and vertex_id < len(shapekey.data):  # Check if vertex is part of the mesh and exists in the shapekey
                    shapekey.data[vertex_id].co.x += position_offset[0]
                    shapekey.data[vertex_id].co.y += position_offset[1]
                    shapekey.data[vertex_id].co.z += position_offset[2]

                    
def create_mesh_from_buffers(vertices, indices, texcoords, color0, color1, object_data, blend_weights, blend_indices, normals,tangents, shapekey_offsets, shapekey_vertex_ids, shapekey_vertex_offsets,component=None):
    flip_texcoord_v = False  # Set this to True if V should be flipped

    for i, (count, start_index) in enumerate(object_data):
        # Create the mesh and object
        mesh = bpy.data.meshes.new(name=f"Component {i}")
        obj = bpy.data.objects.new(name=f"Component {i}", object_data=mesh)
        bpy.context.collection.objects.link(obj)

        # Create faces
        end_index = start_index + count
        if end_index > len(indices):
            end_index = len(indices)  # Adjust to avoid index out of range

        faces = [(indices[j], indices[j+1], indices[j+2]) for j in range(start_index, end_index - 2, 3)]
        mesh.from_pydata(vertices, [], faces)
        mesh.update()

        if color0:
            color_layer0 = mesh.vertex_colors.new(name="COLOR")
            for poly in mesh.polygons:
                for loop_index in poly.loop_indices:
                    loop = mesh.loops[loop_index]
                    loop_vertex_index = loop.vertex_index
                    if loop_vertex_index < len(color0):
                        color_layer0.data[loop_index].color = color0[loop_vertex_index]

        if color1:
            color_layer1 = mesh.vertex_colors.new(name="COLOR1")
            for poly in mesh.polygons:
                for loop_index in poly.loop_indices:
                    loop = mesh.loops[loop_index]
                    loop_vertex_index = loop.vertex_index
                    if loop_vertex_index < len(color1):
                        color_layer1.data[loop_index].color = color1[loop_vertex_index]

        import_uv_layers(mesh, texcoords)
        if blend_weights and blend_indices:
            import_vertex_groups(mesh, obj, blend_indices, blend_weights, component)
        apply_tangents(mesh, tangents)
        apply_normals(obj, mesh, normals)
        # Remove loose vertices
        import_shapekeys(obj,shapekey_offsets, shapekey_vertex_ids, shapekey_vertex_offsets)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.delete_loose()
        bpy.ops.object.mode_set(mode='OBJECT')
        obj.scale = (0.01, 0.01, 0.01)
        obj.rotation_euler[2] = math.radians(180)

        print(f"Mesh {i} created successfully.")
def main():
    # Paths to the .buf files
    base_path = 'F:/WuwaMods/Mods/changlimod/'
    position_buf_path = base_path + '/meshes/Position.buf'
    index_buf_path = base_path + '/meshes/index.buf'
    texcoord_buf_path = base_path + '/meshes/Texcoord.buf'
    color_buf_path = base_path + '/meshes/color.buf'
    blend_buf_path = base_path + '/meshes/blend.buf'
    vector_buf_path = base_path + '/meshes/Vector.buf'
    shape_key_offset_file = base_path + '/meshes/ShapeKeyOffset.buf'
    shape_key_vertex_id_file = base_path + '/meshes/ShapeKeyVertexId.buf'
    shape_key_vertex_offset_file = base_path + '/meshes/ShapeKeyVertexOffset.buf'
    ini_file_path = base_path + 'mod.ini'
    object_data = extract_drawindexed_values(ini_file_path) # if mod has weird toggles add drawindeces manually
    
    vertices = read_position_buffer(position_buf_path)
    indices = read_index_buffer(index_buf_path)
    texcoords0, texcoords1, texcoords2, color1 = read_texcoord_buffer(texcoord_buf_path)
    color0 = read_color_buffer(color_buf_path)
    blend_indices, blend_weights = read_blend_buffer(blend_buf_path)
    tangents, normals = read_vector_buffer(vector_buf_path)    
    texcoords = [texcoords0, texcoords1, texcoords2]
    shapekey_offsets = read_shape_key_offset(shape_key_offset_file)
    shapekey_vertex_ids = read_shape_key_vertex_id(shape_key_vertex_id_file)
    shapekey_vertex_offsets = read_shape_key_vertex_offset(shape_key_vertex_offset_file)
    
    create_mesh_from_buffers(vertices, indices, texcoords, color0, color1, object_data, blend_weights, blend_indices, normals, tangents, shapekey_offsets, shapekey_vertex_ids, shapekey_vertex_offsets)



