from typing import Dict, Any, List, Optional
import binaryninja as bn
from ..core.binary_operations import BinaryOperations


class BinaryNinjaEndpoints:
    def __init__(self, binary_ops: BinaryOperations):
        self.binary_ops = binary_ops

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the binary view"""
        return {
            "loaded": self.binary_ops.current_view is not None,
            "filename": self.binary_ops.current_view.file.filename
            if self.binary_ops.current_view
            else None,
        }

    def get_function_info(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a function"""
        try:
            return self.binary_ops.get_function_info(identifier)
        except Exception as e:
            bn.log_error(f"Error getting function info: {e}")
            return None

    def get_imports(self, offset: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Get list of imported functions"""
        if not self.binary_ops.current_view:
            raise RuntimeError("No binary loaded")

        imports = []
        for sym in self.binary_ops.current_view.get_symbols_of_type(
            bn.SymbolType.ImportedFunctionSymbol
        ):
            imports.append(
                {
                    "name": sym.name,
                    "address": hex(sym.address),
                    "raw_name": sym.raw_name if hasattr(sym, "raw_name") else sym.name,
                    "full_name": sym.full_name
                    if hasattr(sym, "full_name")
                    else sym.name,
                }
            )
        return imports[offset : offset + limit]

    def get_exports(self, offset: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Get list of exported symbols"""
        if not self.binary_ops.current_view:
            raise RuntimeError("No binary loaded")

        exports = []
        for sym in self.binary_ops.current_view.get_symbols():
            if sym.type not in [
                bn.SymbolType.ImportedFunctionSymbol,
                bn.SymbolType.ExternalSymbol,
            ]:
                exports.append(
                    {
                        "name": sym.name,
                        "address": hex(sym.address),
                        "raw_name": sym.raw_name
                        if hasattr(sym, "raw_name")
                        else sym.name,
                        "full_name": sym.full_name
                        if hasattr(sym, "full_name")
                        else sym.name,
                        "type": str(sym.type),
                    }
                )
        return exports[offset : offset + limit]

    def get_namespaces(self, offset: int = 0, limit: int = 100) -> List[str]:
        """Get list of C++ namespaces"""
        if not self.binary_ops.current_view:
            raise RuntimeError("No binary loaded")

        namespaces = set()
        for sym in self.binary_ops.current_view.get_symbols():
            if "::" in sym.name:
                parts = sym.name.split("::")
                if len(parts) > 1:
                    namespace = "::".join(parts[:-1])
                    namespaces.add(namespace)

        sorted_namespaces = sorted(list(namespaces))
        return sorted_namespaces[offset : offset + limit]

    def get_defined_data(
        self, offset: int = 0, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get list of defined data variables"""
        if not self.binary_ops.current_view:
            raise RuntimeError("No binary loaded")

        data_items = []
        for var in self.binary_ops.current_view.data_vars:
            data_type = self.binary_ops.current_view.get_type_at(var)
            value = None

            try:
                if data_type and data_type.width <= 8:
                    value = str(
                        self.binary_ops.current_view.read_int(var, data_type.width)
                    )
                else:
                    value = "(complex data)"
            except (ValueError, TypeError):
                value = "(unreadable)"

            sym = self.binary_ops.current_view.get_symbol_at(var)
            data_items.append(
                {
                    "address": hex(var),
                    "name": sym.name if sym else "(unnamed)",
                    "raw_name": sym.raw_name
                    if sym and hasattr(sym, "raw_name")
                    else None,
                    "value": value,
                    "type": str(data_type) if data_type else None,
                }
            )

        return data_items[offset : offset + limit]

    def search_functions(
        self, search_term: str, offset: int = 0, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Search functions by name"""
        if not self.binary_ops.current_view:
            raise RuntimeError("No binary loaded")

        if not search_term:
            return []

        matches = []
        for func in self.binary_ops.current_view.functions:
            if search_term.lower() in func.name.lower():
                matches.append(
                    {
                        "name": func.name,
                        "address": hex(func.start),
                        "raw_name": func.raw_name
                        if hasattr(func, "raw_name")
                        else func.name,
                        "symbol": {
                            "type": str(func.symbol.type) if func.symbol else None,
                            "full_name": func.symbol.full_name if func.symbol else None,
                        }
                        if func.symbol
                        else None,
                    }
                )

        matches.sort(key=lambda x: x["name"])
        return matches[offset : offset + limit]

    def decompile_function(self, identifier: str) -> Optional[str]:
        """Decompile a function by name or address"""
        try:
            return self.binary_ops.decompile_function(identifier)
        except Exception as e:
            bn.log_error(f"Error decompiling function: {e}")
            return None
