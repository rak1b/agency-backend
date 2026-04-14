import uuid
import datetime
from datetime import timedelta
from rest_framework import status
#from rest_framework import filters
from django.contrib.auth import authenticate
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.pagination import PageNumberPagination
from rest_framework.generics import ListAPIView
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.views import APIView
from rest_framework.response import Response
#from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework import serializers
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from django.shortcuts import render
from rest_framework import filters
from rest_framework import generics, status, permissions
from rest_framework.authtoken.models import Token
from django_filters import FilterSet
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as filters
from django.conf import settings

from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.contrib.auth.models import BaseUserManager
from django.db import models
from .utils import auth_utils

