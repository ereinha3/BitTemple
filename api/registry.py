from .metadata.registry import MetadataRegistry
from .catalog.registry import CatalogRegistry

from functools import cached_property

class APIRegistry:
    @cached_property
    def metadata():
        return MetadataRegistry()

    @cached_property
    def catalog():
        return CatalogRegistry()

    
