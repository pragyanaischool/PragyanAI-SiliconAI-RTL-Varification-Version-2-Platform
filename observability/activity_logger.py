def safe_json_value(
    value: Any,
    *,
    max_depth: int = 6,
    _depth: int = 0,
    _seen: Optional[set[int]] = None,
) -> Any:
    """
    Convert arbitrary Python values into JSON-safe values.

    IMPORTANT:
    This serializer is deliberately cycle-safe.

    Verification state may contain runtime objects such as:
        - ActivityLogger
        - VerificationRun
        - Python logging.Logger
        - agents
        - callbacks
        - exceptions
        - pathlib.Path
        - dictionaries/lists containing references back to parent objects

    Logging must NEVER crash the verification workflow.
    """

    if _seen is None:
        _seen = set()

    # ---------------------------------------------------------
    # Maximum recursion protection
    # ---------------------------------------------------------
    if _depth > max_depth:
        return "<max-depth>"

    # ---------------------------------------------------------
    # JSON-native values
    # ---------------------------------------------------------
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    # ---------------------------------------------------------
    # datetime / date
    # ---------------------------------------------------------
    if isinstance(value, datetime):
        try:
            return value.isoformat()
        except Exception:
            return str(value)

    # ---------------------------------------------------------
    # pathlib.Path
    # ---------------------------------------------------------
    if isinstance(value, Path):
        return str(value)

    # ---------------------------------------------------------
    # bytes
    # ---------------------------------------------------------
    if isinstance(value, bytes):
        try:
            return {
                "type": "bytes",
                "length": len(value),
                "sha256": hashlib.sha256(value).hexdigest(),
            }
        except Exception:
            return "<bytes>"

    # ---------------------------------------------------------
    # Exceptions
    # ---------------------------------------------------------
    if isinstance(value, BaseException):
        try:
            return {
                "type": type(value).__name__,
                "message": str(value),
            }
        except Exception:
            return "<exception>"

    # ---------------------------------------------------------
    # Python logging objects
    # ---------------------------------------------------------
    if isinstance(value, logging.Logger):
        try:
            return {
                "type": "Logger",
                "name": value.name,
            }
        except Exception:
            return "<logger>"

    # ---------------------------------------------------------
    # Cycle detection
    # ---------------------------------------------------------
    try:
        object_id = id(value)

        if object_id in _seen:
            return "<circular-reference>"

        _seen.add(object_id)

    except Exception:
        object_id = None

    try:

        # =====================================================
        # Dictionary
        # =====================================================
        if isinstance(value, dict):

            result: Dict[str, Any] = {}

            for key, item in value.items():

                try:
                    key_text = str(key)

                    # Runtime objects that should NEVER be expanded.
                    if key_text == "logger":
                        result[key_text] = "<logger>"
                        continue

                    if key_text == "verification_run":
                        result[key_text] = "<verification-run>"
                        continue

                    if key_text in {
                        "_logger",
                        "_run_manager",
                        "run_manager",
                        "python_logger",
                    }:
                        result[key_text] = "<runtime-object>"
                        continue

                    result[key_text] = safe_json_value(
                        item,
                        max_depth=max_depth,
                        _depth=_depth + 1,
                        _seen=_seen,
                    )

                except RecursionError:
                    result[str(key)] = "<recursion-error>"

                except Exception:
                    result[str(key)] = "<unserializable>"

            return result

        # =====================================================
        # List / tuple
        # =====================================================
        if isinstance(value, (list, tuple)):

            result = []

            for item in value:

                try:
                    result.append(
                        safe_json_value(
                            item,
                            max_depth=max_depth,
                            _depth=_depth + 1,
                            _seen=_seen,
                        )
                    )

                except RecursionError:
                    result.append("<recursion-error>")

                except Exception:
                    result.append("<unserializable>")

            return result

        # =====================================================
        # Set / frozenset
        # =====================================================
        if isinstance(value, (set, frozenset)):

            result = []

            try:
                items = sorted(value, key=str)
            except Exception:
                items = list(value)

            for item in items:

                try:
                    result.append(
                        safe_json_value(
                            item,
                            max_depth=max_depth,
                            _depth=_depth + 1,
                            _seen=_seen,
                        )
                    )

                except RecursionError:
                    result.append("<recursion-error>")

                except Exception:
                    result.append("<unserializable>")

            return result

        # =====================================================
        # Do NOT recursively inspect arbitrary __dict__
        # =====================================================
        #
        # This is the most important change.
        #
        # The old implementation did:
        #
        #     safe_json_value(vars(value))
        #
        # That can traverse:
        #
        #     ActivityLogger
        #         ↓
        #     Python Logger
        #         ↓
        #     Handler
        #         ↓
        #     Formatter
        #         ↓
        #     ...
        #
        # and eventually recurse forever.
        #
        # Runtime objects should be represented by type/repr only.
        # =====================================================

        if hasattr(value, "__dict__"):

            try:
                class_name = type(value).__name__

                runtime_classes = {
                    "ActivityLogger",
                    "VerificationRun",
                    "RunManager",
                    "Logger",
                    "FileHandler",
                    "StreamHandler",
                    "RotatingFileHandler",
                    "TimedRotatingFileHandler",
                    "Formatter",
                }

                if class_name in runtime_classes:
                    return f"<{class_name}>"

                # Never walk arbitrary object.__dict__.
                return {
                    "type": class_name,
                    "repr": _safe_repr(value),
                }

            except RecursionError:
                return "<repr-recursion-error>"

            except Exception:
                try:
                    return f"<{type(value).__name__}>"
                except Exception:
                    return "<object>"

        # =====================================================
        # Already JSON serializable
        # =====================================================
        try:
            json.dumps(value)
            return value
        except Exception:
            pass

        # =====================================================
        # Last resort
        # =====================================================
        return _safe_repr(value)

    except RecursionError:
        return "<recursion-error>"

    except Exception:
        try:
            return f"<unserializable:{type(value).__name__}>"
        except Exception:
            return "<unserializable>"

    finally:

        # Remove from traversal path so the same object can safely
        # appear in another independent branch.
        if object_id is not None:

            try:
                _seen.discard(object_id)
            except Exception:
                pass


def _safe_repr(
    value: Any,
    max_length: int = 2000,
) -> str:
    """
    Safely create a bounded repr().

    repr() itself can theoretically trigger recursion,
    so this function is also defensive.
    """

    try:

        text = repr(value)

        if len(text) > max_length:
            return text[:max_length] + "...<truncated>"

        return text

    except RecursionError:
        return "<repr-recursion-error>"

    except Exception:

        try:
            return f"<{type(value).__name__}>"
        except Exception:
            return "<unrepresentable>"
