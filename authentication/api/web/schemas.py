"""
OpenAPI schemas for authentication API endpoints.
"""
from drf_spectacular.utils import OpenApiParameter, OpenApiExample, inline_serializer
from drf_spectacular.types import OpenApiTypes
from rest_framework import serializers


def get_order_history_parameters():
    """Get OpenAPI parameters for order history API."""
    return [
        OpenApiParameter(
            name='number',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.PATH,
            description='Order number',
            required=True
        ),
        OpenApiParameter(
            name='start_date',
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            description='Filter history records starting from this date'
        ),
        OpenApiParameter(
            name='end_date',
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            description='Filter history records up to this date'
        )
    ]


def get_order_history_response_serializer():
    """Get inline serializer for order history response."""
    from .serializers import HistorySerializer
    
    # Use inline_serializer without nesting HistorySerializer to avoid serialization issues
    # Instead, we'll use a generic object type for the history arrays
    return inline_serializer(
        name='OrderHistoryResponse',
        fields={
            'order_number': serializers.CharField(),
            'order_id': serializers.IntegerField(),
            'order_history': serializers.ListField(
                child=serializers.DictField(),
                help_text='Array of order history records'
            ),
            'order_terminals_history': serializers.ListField(
                child=inline_serializer(
                    name='OrderTerminalHistoryItem',
                    fields={
                        'terminal_id': serializers.IntegerField(),
                        'terminal_number': serializers.CharField(),
                        'tid': serializers.CharField(),
                        'history': serializers.ListField(
                            child=serializers.DictField(),
                            help_text='Array of terminal history records'
                        )
                    }
                ),
                help_text='Array of terminal history objects'
            ),
            'order_accessories_history': serializers.ListField(
                child=inline_serializer(
                    name='OrderAccessoryHistoryItem',
                    fields={
                        'accessory_id': serializers.IntegerField(),
                        'accessory_number': serializers.CharField(),
                        'history': serializers.ListField(
                            child=serializers.DictField(),
                            help_text='Array of accessory history records'
                        )
                    }
                ),
                help_text='Array of accessory history objects'
            ),
            'software_addons_history': serializers.ListField(
                child=inline_serializer(
                    name='SoftwareAddonHistoryItem',
                    fields={
                        'addon_id': serializers.IntegerField(),
                        'software_addon_name': serializers.CharField(),
                        'history': serializers.ListField(
                            child=serializers.DictField(),
                            help_text='Array of addon history records'
                        )
                    }
                ),
                help_text='Array of software addon history objects'
            )
        }
    )


def get_order_history_responses():
    """Get OpenAPI responses schema for order history API."""
    return {
        200: get_order_history_response_serializer(),
        404: inline_serializer(
            name='ErrorResponse',
            fields={'detail': serializers.CharField()}
        ),
        500: inline_serializer(
            name='ErrorResponse',
            fields={'detail': serializers.CharField()}
        )
    }

