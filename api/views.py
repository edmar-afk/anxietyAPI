# views.py
from rest_framework import generics, permissions, views
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth.models import User
from rest_framework import status, viewsets
from .serializers import UserSerializer, ChatbotSerializer
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.views import View
from rest_framework.decorators import api_view, permission_classes
from django.db.models import Q, Max
from django.contrib.auth import get_user_model
from rest_framework.generics import RetrieveAPIView



import spacy
from rest_framework import viewsets, status
from rest_framework.response import Response
from django.conf import settings
import json
import os

class CreateUserView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        # Extract user data from request
        user_data = self.request.data
        username = user_data.get('username')
        
      
        # Check if the username, email, or mobile number already exists
        if User.objects.filter(username=username).exists():
            raise ValidationError({'username': 'A user with this Mobile Number already exists.'})
        
        # Save the user and profile
        serializer.save()


class UserDetailView(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user







# Load spaCy language model
model_path = os.path.join(settings.BASE_DIR, 'en_core_web_md')
nlp = spacy.load(model_path) if os.path.exists(model_path) else spacy.load("en_core_web_md")

BASE_DIR = settings.BASE_DIR

# Load knowledge base from a JSON file
def load_knowledge_base(file_path: str):
    full_path = os.path.join(BASE_DIR, file_path)
    with open(full_path, 'r') as file:
        data = json.load(file)
    return data

# Get the answer for a specific question
def get_answer_for_question(question: str, knowledge_base: dict) -> str | None:
    for q in knowledge_base["questions"]:
        if q["question"] == question:
            return q["answer"]
    return None

# Find the best match using spaCy similarity
def find_best_match(user_question: str, questions: list[str]) -> str | None:
    user_question_doc = nlp(user_question)
    best_match = None
    best_similarity = 0.6  # Adjust the threshold as needed

    for question in questions:
        question_doc = nlp(question)
        similarity = user_question_doc.similarity(question_doc)
        if similarity > best_similarity:
            best_similarity = similarity
            best_match = question

    return best_match

class ChatbotViewSet(viewsets.ViewSet):
    # Your ChatbotSerializer here
    serializer_class = ChatbotSerializer
    authentication_classes = []
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            user_question = serializer.validated_data['question']
            knowledge_base = load_knowledge_base('knowledge_base.json')
            questions = [q["question"] for q in knowledge_base["questions"]]
            best_match = find_best_match(user_question, questions)

            if best_match:
                answer = get_answer_for_question(best_match, knowledge_base)
                if answer:
                    formatted_answer = answer.replace('|', '\n').strip()
                    return Response({'answer': formatted_answer}, status=status.HTTP_200_OK)
                else:
                    return Response({'answer': "No answer found."}, status=status.HTTP_200_OK)
            else:
                return Response({'answer': "Sorry, I didn't understand the question."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)