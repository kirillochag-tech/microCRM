from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from django.db.models import Q
from .models import Task, SurveyAnswer, SurveyAnswerGroupReadStatus
from clients.models import Client
from users.models import CustomUser
import json


def getGroupedAnswers(request):
    """API endpoint to get grouped survey answers"""
    task_id = request.GET.get('task_id')
    client_id = request.GET.get('client_id')
    user_id = request.GET.get('user_id')
    
    filters = Q()
    if task_id:
        filters &= Q(question__task_id=task_id)
    if client_id:
        filters &= Q(client_id=client_id)
    if user_id:
        filters &= Q(user_id=user_id)
    
    answers = SurveyAnswer.objects.filter(filters).select_related(
        'user', 'question', 'client'
    ).prefetch_related('selected_choices', 'photos')
    
    data = []
    for answer in answers:
        item = {
            'id': answer.id,
            'user': answer.user.get_full_name() or answer.user.username,
            'client': answer.client.name,
            'question': answer.question.question_text,
            'text_answer': answer.text_answer,
            'created_at': answer.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'has_photos': answer.photos.exists(),
        }
        
        if answer.selected_choices.exists():
            item['selected_choices'] = [
                choice.choice_text for choice in answer.selected_choices.all()
            ]
        
        data.append(item)
    
    return JsonResponse({'results': data})


@csrf_exempt
def markAsRead(request):
    """API endpoint to mark survey answers as read"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            task_id = data.get('task_id')
            client_id = data.get('client_id')
            user_id = data.get('user_id')
            
            # Create or update the read status
            read_status, created = SurveyAnswerGroupReadStatus.objects.get_or_create(
                task_id=task_id,
                client_id=client_id,
                user_id=user_id,
                defaults={
                    'read_by_id': request.user.id if request.user.is_authenticated else None
                }
            )
            
            if not created:
                read_status.read_by = request.user if request.user.is_authenticated else None
                read_status.save()
                
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


def autocomplete_clients(request):
    """API endpoint for client autocomplete"""
    query = request.GET.get('term', '')
    if len(query) < 2:
        return JsonResponse([], safe=False)
    
    clients = Client.objects.filter(
        Q(name__icontains=query) | Q(phone__icontains=query)
    )[:10]
    
    data = [{'id': client.id, 'name': client.name} for client in clients]
    return JsonResponse(data, safe=False)


def autocomplete_tasks(request):
    """API endpoint for task autocomplete"""
    query = request.GET.get('term', '')
    if len(query) < 2:
        return JsonResponse([], safe=False)
    
    tasks = Task.objects.filter(title__icontains=query)[:10]
    
    data = [{'id': task.id, 'name': task.title} for task in tasks]
    return JsonResponse(data, safe=False)