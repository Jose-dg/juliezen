from django.shortcuts import render
from django.http import JsonResponse

# Create your views here.


def healthcheck(_request):
    return JsonResponse({"status": "ok"})
