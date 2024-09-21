import struct


def read_formated_data(file_path:str,format:str) -> list:
    file_data = []
    read_file = open(file_path, 'rb') 
    if format == "DXGI_FORMAT_R32_UINT":
        while chunk := read_file.read(4):
            file_data.append(struct.unpack('<I', chunk)[0])
    elif format == "DXGI_FORMAT_R16_UINT":
        while chunk := read_file.read(2):
            file_data.append(struct.unpack('<H', chunk)[0])

    elif format == "R32G32B32_FLOAT":    
        while chunk := read_file.read(12):  
            x, y, z = struct.unpack('<3f', chunk)
            file_data.append((x, y, z))
    elif format == "R32G32B32A32_FLOAT":
        while chunk := read_file.read(16):  
            x, y, z, w = struct.unpack('<4f', chunk)
            file_data.append((x, y, z, w))

    elif format == "R8G8B8A8_SNORM":
        while chunk := read_file.read(4): 
            nx, ny, nz, nw = struct.unpack('<4b', chunk)
            file_data.append((nx / 127.0, ny / 127.0, nz / 127.0, nw / 127.0))
    elif format == "R8G8B8A8_UNORM":
        while chunk := read_file.read(4): 
            r, g, b, a = struct.unpack('<4B', chunk)
            file_data.append((r / 255.0, g / 255.0, b / 255.0, a / 255.0))
    read_file.close()
    return file_data
