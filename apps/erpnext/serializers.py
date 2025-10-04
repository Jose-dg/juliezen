
from rest_framework import serializers


class ItemSerializer(serializers.Serializer):
    """
    A pass-through serializer that represents the raw JSON data
    of an Item document from ERPNext.
    """
    # This serializer is intentionally left without fields to simply act as a
    # container for the raw dictionary data returned by the service.
    pass



