"""Main Locust entry point — imports all user classes and shapes for auto-discovery."""

# User classes
from loadtests.users.crud_user import CrudUser  # noqa: F401
from loadtests.users.mixed_user import MixedUser  # noqa: F401
from loadtests.users.stream_user import StreamUser  # noqa: F401

# Load shapes (uncomment the one you want, or use --class-picker in Locust UI)
# from loadtests.shapes.staged_shape import StagedShape  # noqa: F401
# from loadtests.shapes.crud_only_shape import CrudOnlyShape  # noqa: F401
