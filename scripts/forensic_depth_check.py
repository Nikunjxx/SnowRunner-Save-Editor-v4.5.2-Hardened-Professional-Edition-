import json
import sys

def iterative_depth_check(file_path):
    with open(file_path, "rb") as f:
        raw = f.read()
    text = raw[:-1].decode("utf-8", errors="replace")
    data = json.loads(text)
    
    max_depth = 0
    stack = [(data, 0)] # (node, current_depth)
    
    while stack:
        node, depth = stack.pop()
        max_depth = max(max_depth, depth)
        
        if depth > 10000:
             print(f"CRITICAL: Infinite depth detected at depth {depth}!")
             return depth

        if isinstance(node, dict):
            for v in node.values():
                stack.append((v, depth + 1))
        elif isinstance(node, list):
            for i in node:
                stack.append((i, depth + 1))
                
    return max_depth

if __name__ == "__main__":
    p = r"E:\Snow Runner New Tool\test_data\steam_live_mirror\CompleteSave.cfg"
    print(f"Analytical Depth of {p}:", iterative_depth_check(p))
