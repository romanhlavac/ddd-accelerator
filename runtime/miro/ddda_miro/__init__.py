"""DDDA Miro renderer and synchronization runtime."""

from .image_read_normalization_adapter import install_image_read_normalization_adapter
from .image_upload_adapter import install_image_upload_adapter
from .multipart_image_read_normalization_adapter import install_multipart_image_read_normalization_adapter

__version__ = "0.2.0"

install_image_upload_adapter()
install_image_read_normalization_adapter()
install_multipart_image_read_normalization_adapter()
