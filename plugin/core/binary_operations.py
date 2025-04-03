import binaryninja as bn
from typing import Optional, List, Dict, Any, Union
from .config import BinaryNinjaConfig


class BinaryOperations:
    def __init__(self, config: BinaryNinjaConfig):
        self.config = config
        self._current_view: Optional[bn.BinaryView] = None

    @property
    def current_view(self) -> Optional[bn.BinaryView]:
        return self._current_view

    @current_view.setter
    def current_view(self, bv: Optional[bn.BinaryView]):
        self._current_view = bv
        if bv:
            bn.log_info(f"Set current binary view: {bv.file.filename}")
        else:
            bn.log_info("Cleared current binary view")

    def load_binary(self, filepath: str) -> bn.BinaryView:
        """Load a binary file using the appropriate method based on the Binary Ninja API version"""
        try:
            if hasattr(bn, "open_view"):
                bn.log_info("Using bn.open_view method")
                self._current_view = bn.open_view(filepath)
            elif hasattr(bn, "BinaryViewType") and hasattr(
                bn.BinaryViewType, "get_view_of_file"
            ):
                bn.log_info("Using BinaryViewType.get_view_of_file method")
                file_metadata = bn.FileMetadata()
                try:
                    if hasattr(bn.BinaryViewType, "get_default_options"):
                        options = bn.BinaryViewType.get_default_options()
                        self._current_view = bn.BinaryViewType.get_view_of_file(
                            filepath, file_metadata, options
                        )
                    else:
                        self._current_view = bn.BinaryViewType.get_view_of_file(
                            filepath, file_metadata
                        )
                except TypeError:
                    self._current_view = bn.BinaryViewType.get_view_of_file(filepath)
            else:
                bn.log_info("Using legacy method")
                file_metadata = bn.FileMetadata()
                binary_view_type = bn.BinaryViewType.get_view_of_file_with_options(
                    filepath, file_metadata
                )
                if binary_view_type:
                    self._current_view = binary_view_type.open()
                else:
                    raise Exception("No view type available for this file")

            return self._current_view
        except Exception as e:
            bn.log_error(f"Failed to load binary: {e}")
            raise

    def get_function_by_name_or_address(
        self, identifier: Union[str, int]
    ) -> Optional[bn.Function]:
        """Get a function by either its name or address.

        Args:
            identifier: Function name or address (can be int, hex string, or decimal string)

        Returns:
            Function object if found, None otherwise
        """
        if not self._current_view:
            raise RuntimeError("No binary loaded")

        # Handle address-based lookup
        try:
            if isinstance(identifier, str) and identifier.startswith("0x"):
                addr = int(identifier, 16)
            elif isinstance(identifier, (int, str)):
                addr = int(identifier) if isinstance(identifier, str) else identifier

            func = self._current_view.get_function_at(addr)
            if func:
                bn.log_info(f"Found function at address {hex(addr)}: {func.name}")
                return func
        except ValueError:
            pass

        # Handle name-based lookup with case sensitivity
        for func in self._current_view.functions:
            if func.name == identifier:
                bn.log_info(f"Found function by name: {func.name}")
                return func

        # Try case-insensitive match as fallback
        for func in self._current_view.functions:
            if func.name.lower() == str(identifier).lower():
                bn.log_info(f"Found function by case-insensitive name: {func.name}")
                return func

        # Try symbol table lookup as last resort
        symbol = self._current_view.get_symbol_by_raw_name(str(identifier))
        if symbol and symbol.address:
            func = self._current_view.get_function_at(symbol.address)
            if func:
                bn.log_info(f"Found function through symbol lookup: {func.name}")
                return func

        bn.log_error(f"Could not find function: {identifier}")
        return None

    def get_function_names(
        self, offset: int = 0, limit: int = 100
    ) -> List[Dict[str, str]]:
        """Get list of function names with addresses"""
        if not self._current_view:
            raise RuntimeError("No binary loaded")

        functions = []
        for func in self._current_view.functions:
            functions.append(
                {
                    "name": func.name,
                    "address": hex(func.start),
                    "raw_name": func.raw_name
                    if hasattr(func, "raw_name")
                    else func.name,
                }
            )

        return functions[offset : offset + limit]

    def get_class_names(self, offset: int = 0, limit: int = 100) -> List[str]:
        """Get list of class names with pagination"""
        if not self._current_view:
            raise RuntimeError("No binary loaded")

        class_names = set()

        try:
            # Try different methods to identify classes
            for type_obj in self._current_view.types.values():
                try:
                    # Skip None or invalid types
                    if not type_obj or not hasattr(type_obj, "name"):
                        continue

                    # Method 1: Check type_class attribute
                    if hasattr(type_obj, "type_class"):
                        class_names.add(type_obj.name)
                        continue

                    # Method 2: Check structure attribute
                    if hasattr(type_obj, "structure") and type_obj.structure:
                        structure = type_obj.structure

                        # Check various attributes that indicate a class
                        if any(
                            hasattr(structure, attr)
                            for attr in [
                                "vtable",
                                "base_structures",
                                "members",
                                "functions",
                            ]
                        ):
                            class_names.add(type_obj.name)
                            continue

                        # Check type attribute if available
                        if hasattr(structure, "type"):
                            type_str = str(structure.type).lower()
                            if "class" in type_str or "struct" in type_str:
                                class_names.add(type_obj.name)
                                continue

                except Exception as e:
                    bn.log_debug(
                        f"Error processing type {getattr(type_obj, 'name', '<unknown>')}: {e}"
                    )
                    continue

            bn.log_info(f"Found {len(class_names)} classes")
            sorted_names = sorted(list(class_names))
            return sorted_names[offset : offset + limit]

        except Exception as e:
            bn.log_error(f"Error getting class names: {e}")
            return []

    def get_segments(self, offset: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Get list of segments with pagination"""
        if not self._current_view:
            raise RuntimeError("No binary loaded")

        segments = []
        for segment in self._current_view.segments:
            segment_info = {
                "start": hex(segment.start),
                "end": hex(segment.end),
                "name": "",
                "flags": [],
            }

            # Try to get segment name if available
            if hasattr(segment, "name"):
                segment_info["name"] = segment.name
            elif hasattr(segment, "data_name"):
                segment_info["name"] = segment.data_name

            # Try to get segment flags safely
            if hasattr(segment, "flags"):
                try:
                    if isinstance(segment.flags, (list, tuple)):
                        segment_info["flags"] = list(segment.flags)
                    else:
                        segment_info["flags"] = [str(segment.flags)]
                except (AttributeError, TypeError, ValueError):
                    pass

            # Add segment permissions if available
            if hasattr(segment, "readable"):
                segment_info["readable"] = bool(segment.readable)
            if hasattr(segment, "writable"):
                segment_info["writable"] = bool(segment.writable)
            if hasattr(segment, "executable"):
                segment_info["executable"] = bool(segment.executable)

            segments.append(segment_info)

        return segments[offset : offset + limit]

    def rename_function(self, old_name: str, new_name: str) -> bool:
        """Rename a function using multiple fallback methods.

        Args:
            old_name: Current function name or address
            new_name: New name for the function

        Returns:
            True if rename succeeded, False otherwise
        """
        if not self._current_view:
            raise RuntimeError("No binary loaded")

        try:
            func = self.get_function_by_name_or_address(old_name)
            if not func:
                bn.log_error(f"Function not found: {old_name}")
                return False

            bn.log_info(f"Found function to rename: {func.name} at {hex(func.start)}")

            if not new_name or not isinstance(new_name, str):
                bn.log_error(f"Invalid new name: {new_name}")
                return False

            if not hasattr(func, "name") or not hasattr(func, "__setattr__"):
                bn.log_error(f"Function {func.name} cannot be renamed (read-only)")
                return False

            try:
                # Try direct name assignment first
                old_name = func.name
                func.name = new_name

                if func.name == new_name:
                    bn.log_info(
                        f"Successfully renamed function from {old_name} to {new_name}"
                    )
                    return True

                # Try symbol-based renaming if direct assignment fails
                if hasattr(func, "symbol") and func.symbol:
                    try:
                        new_symbol = bn.Symbol(
                            func.symbol.type,
                            func.start,
                            new_name,
                            namespace=func.symbol.namespace
                            if hasattr(func.symbol, "namespace")
                            else None,
                        )
                        self._current_view.define_user_symbol(new_symbol)
                        bn.log_info("Successfully renamed function using symbol table")
                        return True
                    except Exception as e:
                        bn.log_error(f"Symbol-based rename failed: {e}")

                # Try function update method as last resort
                if hasattr(self._current_view, "update_function"):
                    try:
                        func_copy = func
                        func_copy.name = new_name
                        self._current_view.update_function(func)
                        bn.log_info("Successfully renamed function using update method")
                        return True
                    except Exception as e:
                        bn.log_error(f"Function update rename failed: {e}")

                bn.log_error(
                    f"All rename methods failed - function name unchanged: {func.name}"
                )
                return False

            except Exception as e:
                bn.log_error(f"Error during rename operation: {e}")
                return False

        except Exception as e:
            bn.log_error(f"Error in rename_function: {e}")
            return False

    def get_function_info(
        self, identifier: Union[str, int]
    ) -> Optional[Dict[str, Any]]:
        """Get detailed information about a function"""
        if not self._current_view:
            raise RuntimeError("No binary loaded")

        func = self.get_function_by_name_or_address(identifier)
        if not func:
            return None

        bn.log_info(f"Found function: {func.name} at {hex(func.start)}")

        info = {
            "name": func.name,
            "raw_name": func.raw_name if hasattr(func, "raw_name") else func.name,
            "address": hex(func.start),
            "symbol": None,
        }

        if func.symbol:
            info["symbol"] = {
                "type": str(func.symbol.type),
                "full_name": func.symbol.full_name
                if hasattr(func.symbol, "full_name")
                else func.symbol.name,
            }

        return info

    def decompile_function(self, identifier: Union[str, int]) -> Optional[str]:
        """Decompile a function to its high-level representation.

        Args:
            identifier: Function name or address

        Returns:
            Decompiled function code as string, or None if decompilation fails
        """
        if not self._current_view:
            raise RuntimeError("No binary loaded")

        func = self.get_function_by_name_or_address(identifier)
        if not func:
            return None

        try:
            # Try high-level IL first for best readability
            if hasattr(func, "hlil"):
                return str(func.hlil)
            # Fall back to medium-level IL if available
            elif hasattr(func, "mlil"):
                return str(func.mlil)
            # Use basic function representation as last resort
            else:
                return str(func)
        except Exception as e:
            bn.log_error(f"Error decompiling function: {str(e)}")
            return None

    def rename_data(self, address: int, new_name: str) -> bool:
        """Rename data at a specific address"""
        if not self._current_view:
            raise RuntimeError("No binary loaded")

        try:
            if self._current_view.is_valid_offset(address):
                self._current_view.define_user_symbol(
                    bn.Symbol(bn.SymbolType.DataSymbol, address, new_name)
                )
                return True
        except Exception as e:
            bn.log_error(f"Failed to rename data: {e}")
        return False

    def get_defined_data(
        self, offset: int = 0, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get list of defined data variables"""
        if not self._current_view:
            raise RuntimeError("No binary loaded")

        data_items = []
        for var in self._current_view.data_vars:
            data_type = None
            value = None

            try:
                # Try to get data type safely
                if hasattr(self._current_view, "get_type_at"):
                    data_type = self._current_view.get_type_at(var)
                elif hasattr(self._current_view, "get_data_var_at"):
                    data_type = self._current_view.get_data_var_at(var)

                # Try to read value if type is available and small enough
                if data_type and hasattr(data_type, "width") and data_type.width <= 8:
                    try:
                        value = str(self._current_view.read_int(var, data_type.width))
                    except (ValueError, RuntimeError):
                        value = "(unreadable)"
                else:
                    value = "(complex data)"
            except (AttributeError, TypeError, ValueError, RuntimeError):
                value = "(unknown)"
                data_type = None

            # Get symbol information
            sym = self._current_view.get_symbol_at(var)
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

    def set_comment(self, address: int, comment: str) -> bool:
        """Set a comment at a specific address.

        Args:
            address: The address to set the comment at
            comment: The comment text to set

        Returns:
            True if the comment was set successfully, False otherwise
        """
        if not self._current_view:
            raise RuntimeError("No binary loaded")

        try:
            if not self._current_view.is_valid_offset(address):
                bn.log_error(f"Invalid address for comment: {hex(address)}")
                return False

            self._current_view.set_comment_at(address, comment)
            bn.log_info(f"Set comment at {hex(address)}: {comment}")
            return True
        except Exception as e:
            bn.log_error(f"Failed to set comment: {e}")
            return False

    def set_function_comment(self, identifier: Union[str, int], comment: str) -> bool:
        """Set a comment for a function.

        Args:
            identifier: Function name or address
            comment: The comment text to set

        Returns:
            True if the comment was set successfully, False otherwise
        """
        if not self._current_view:
            raise RuntimeError("No binary loaded")

        try:
            func = self.get_function_by_name_or_address(identifier)
            if not func:
                bn.log_error(f"Function not found: {identifier}")
                return False

            self._current_view.set_comment_at(func.start, comment)
            bn.log_info(f"Set comment for function {func.name} at {hex(func.start)}: {comment}")
            return True
        except Exception as e:
            bn.log_error(f"Failed to set function comment: {e}")
            return False

    def get_comment(self, address: int) -> Optional[str]:
        """Get the comment at a specific address.

        Args:
            address: The address to get the comment from

        Returns:
            The comment text if found, None otherwise
        """
        if not self._current_view:
            raise RuntimeError("No binary loaded")

        try:
            if not self._current_view.is_valid_offset(address):
                bn.log_error(f"Invalid address for comment: {hex(address)}")
                return None

            comment = self._current_view.get_comment_at(address)
            return comment if comment else None
        except Exception as e:
            bn.log_error(f"Failed to get comment: {e}")
            return None

    def get_function_comment(self, identifier: Union[str, int]) -> Optional[str]:
        """Get the comment for a function.

        Args:
            identifier: Function name or address

        Returns:
            The comment text if found, None otherwise
        """
        if not self._current_view:
            raise RuntimeError("No binary loaded")

        try:
            func = self.get_function_by_name_or_address(identifier)
            if not func:
                bn.log_error(f"Function not found: {identifier}")
                return None

            comment = self._current_view.get_comment_at(func.start)
            return comment if comment else None
        except Exception as e:
            bn.log_error(f"Failed to get function comment: {e}")
            return None

    def delete_comment(self, address: int) -> bool:
        """Delete a comment at a specific address"""
        if not self._current_view:
            raise RuntimeError("No binary loaded")

        try:
            if self._current_view.is_valid_offset(address):
                self._current_view.set_comment_at(address, None)
                return True
        except Exception as e:
            bn.log_error(f"Failed to delete comment: {e}")
        return False

    def delete_function_comment(self, identifier: Union[str, int]) -> bool:
        """Delete a comment for a function"""
        if not self._current_view:
            raise RuntimeError("No binary loaded")

        try:
            func = self.get_function_by_name_or_address(identifier)
            if not func:
                return False
                
            func.comment = None
            return True
        except Exception as e:
            bn.log_error(f"Failed to delete function comment: {e}")
        return False
