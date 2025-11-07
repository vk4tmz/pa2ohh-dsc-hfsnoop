
import struct


S16BE = "<" 
S16LE = ">"

def read_s16(inp_stream, frame_len: int, endianness:str=S16BE):
    
    data = inp_stream.read(frame_len * 2)
    if not data:
        return []
    
    int_list = []
    idx = 0;
    while idx < len(data):
        
        try:
            two_bytes = data[idx:idx+2]
            value = struct.unpack(f'{endianness}h', two_bytes)[0]
            int_list.append(value)
            idx += 2
        except struct.error as e:
            # Handle cases where incomplete data is read at the end
            print(f"Warning: Incomplete 16-bit integer detected at end of input. {e}")
            break
    return int_list

def read_s16be(inp_stream, frame_len: int):
    return read_s16(inp_stream, frame_len, S16BE)

def read_s16le(inp_stream, frame_len: int):
    return read_s16(inp_stream, frame_len, S16LE)
