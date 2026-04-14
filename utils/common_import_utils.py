from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated  # if you want auth
from utils.pagination_utils import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema
from rest_framework.filters import SearchFilter
from authentication.permissions import HasCustomPermission
from authentication.base import BaseModelViewSet    
from rest_framework.parsers import MultiPartParser
from django.core.exceptions import ValidationError
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from rest_framework.filters import SearchFilter
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
import logging
from datetime import datetime
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin

# Configure the logger
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('django')

def print_log(message: str, title: str = "Log", level: str = "INFO"):
    """
    Print formatted log message with specified log level.
    
    Args:
        message: The log message to display
        title: Title/header for the log entry (default: "Log")
        level: Log level - one of 'INFO', 'WARNING', 'ERROR', 'DEBUG' (default: "INFO")
    
    Example:
        print_log("Order created successfully", "Order Creation", "INFO")
        print_log("Failed to process order", "Order Processing", "ERROR")
        print_log("Low stock warning", "Inventory Check", "WARNING")
    """
    # Validate log level
    valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    if level.upper() not in valid_levels:
        level = 'INFO'  # Default to INFO if invalid level provided
    else:
        level = level.upper()
    
    # Get the appropriate logger method based on level
    log_method = getattr(logger, level.lower(), logger.info)
    
    separator = "----------------------------------------"
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Log the formatted message
    log_method("\n")
    log_method(separator)
    log_method(f"{timestamp} - {title} [{level}]")
    log_method(separator)
    log_method(message)
    log_method(separator)
    log_method("\n")
