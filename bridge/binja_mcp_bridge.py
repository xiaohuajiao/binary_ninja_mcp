from mcp.server.fastmcp import FastMCP
import requests


binja_server_url = "http://localhost:9009"
mcp = FastMCP("binja-mcp", log_level="ERROR")


# def safe_get(endpoint: str, params: dict = None) -> list:
#     """
#     Perform a GET request. If 'params' is given, we convert it to a query string.
#     """
#     if params is None:
#         params = {}
#     qs = [f"{k}={v}" for k, v in params.items()]
#     query_string = "&".join(qs)
#     url = f"{binja_server_url}/{endpoint}"
#     if query_string:
#         url += "?" + query_string

#     try:
#         response = requests.get(url, timeout=5)
#         response.encoding = "utf-8"
#         if response.ok:
#             return response.text.splitlines()
#         else:
#             return [f"Error {response.status_code}: {response.text.strip()}"]
#     except Exception as e:
#         return [f"Request failed: {str(e)}"]


def safe_post(endpoint: str, data: dict | str) -> str:
    try:
        if isinstance(data, dict):
            response = requests.post(
                f"{binja_server_url}/{endpoint}", data=data, timeout=5
            )
        else:
            response = requests.post(
                f"{binja_server_url}/{endpoint}", data=data.encode("utf-8"), timeout=5
            )
        response.encoding = "utf-8"
        if response.ok:
            return response.text.strip()
        else:
            return f"Error {response.status_code}: {response.text.strip()}"
    except Exception as e:
        return f"Request failed: {str(e)}"


@mcp.tool()
def list_methods(offset: int = 0, limit: int = 100) -> list:
    """
    List all function names in the program with pagination.
    """
    return safe_post("methods", {"offset": offset, "limit": limit})


@mcp.tool()
def list_classes(offset: int = 0, limit: int = 100) -> list:
    """
    List all namespace/class names in the program with pagination.
    """
    return safe_post("classes", {"offset": offset, "limit": limit})


@mcp.tool()
def decompile_function(name: str) -> str:
    """
    Decompile a specific function by name and return the decompiled C code.
    """
    return safe_post("decompile", name)


@mcp.tool()
def rename_function(old_name: str, new_name: str) -> str:
    """
    Rename a function by its current name to a new user-defined name.
    """
    return safe_post("renameFunction", {"oldName": old_name, "newName": new_name})


@mcp.tool()
def rename_data(address: str, new_name: str) -> str:
    """
    Rename a data label at the specified address.
    """
    return safe_post("renameData", {"address": address, "newName": new_name})


@mcp.tool()
def set_comment(address: str, comment: str) -> str:
    """
    Set a comment at a specific address.
    """
    return safe_post("comment", {"address": address, "comment": comment})


@mcp.tool()
def set_function_comment(function_name: str, comment: str) -> str:
    """
    Set a comment for a function.
    """
    return safe_post("comment/function", {"name": function_name, "comment": comment})


@mcp.tool()
def get_comment(address: str) -> str:
    """
    Get the comment at a specific address.
    """
    return safe_post("comment", {"address": address})[0]


@mcp.tool()
def get_function_comment(function_name: str) -> str:
    """
    Get the comment for a function.
    """
    return safe_post("comment/function", {"name": function_name})[0]


@mcp.tool()
def list_segments(offset: int = 0, limit: int = 100) -> list:
    """
    List all memory segments in the program with pagination.
    """
    return safe_post("segments", {"offset": offset, "limit": limit})


@mcp.tool()
def list_imports(offset: int = 0, limit: int = 100) -> list:
    """
    List imported symbols in the program with pagination.
    """
    return safe_post("imports", {"offset": offset, "limit": limit})


@mcp.tool()
def list_exports(offset: int = 0, limit: int = 100) -> list:
    """
    List exported functions/symbols with pagination.
    """
    return safe_post("exports", {"offset": offset, "limit": limit})


@mcp.tool()
def list_namespaces(offset: int = 0, limit: int = 100) -> list:
    """
    List all non-global namespaces in the program with pagination.
    """
    return safe_post("namespaces", {"offset": offset, "limit": limit})


@mcp.tool()
def list_data_items(offset: int = 0, limit: int = 100) -> list:
    """
    List defined data labels and their values with pagination.
    """
    return safe_post("data", {"offset": offset, "limit": limit})


@mcp.tool()
def search_functions_by_name(query: str, offset: int = 0, limit: int = 100) -> list:
    """
    Search for functions whose name contains the given substring.
    """
    if not query:
        return ["Error: query string is required"]
    return safe_post(
        "searchFunctions", {"query": query, "offset": offset, "limit": limit}
    )


@mcp.tool()
def get_binary_status() -> str:
    """
    Get the current status of the loaded binary.
    """
    return safe_post("status")[0]


@mcp.tool()
def delete_comment(address: str) -> str:
    """
    Delete the comment at a specific address.
    """
    return safe_post("comment", {"address": address, "_method": "DELETE"})


@mcp.tool()
def delete_function_comment(function_name: str) -> str:
    """
    Delete the comment for a function.
    """
    return safe_post("comment/function", {"name": function_name, "_method": "DELETE"})


if __name__ == "__main__":
    print("Starting MCP bridge service...")
    mcp.run()
