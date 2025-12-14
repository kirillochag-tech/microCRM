# -*- coding: utf-8 -*-
"""
Created on Fri Nov 28 23:40:06 2025

@author: Professional
"""

"""
Reporting services for analytics and statistics generation.

This module provides business logic for generating and processing
task statistics and analytics data.
"""

from django.db.models import Count, Q
from django.utils import timezone
import json
from collections import defaultdict

from tasks.models import Task, SurveyAnswer, SurveyQuestion, PhotoReport
from .models import TaskStatistics

class StatisticsGenerator:
    """Service for generating task statistics."""
    
    @staticmethod
    def generate_survey_statistics(task):
        """Generate statistics for survey tasks."""
        stats = {}
        total_responses = 0
        
        for question in task.questions.all():
            question_stats = {
                'question_text': question.question_text,
                'question_type': question.question_type,
                'answers': defaultdict(int),
                'total': 0
            }
            
            answers = SurveyAnswer.objects.filter(question=question)
            question_stats['total'] = answers.count()
            total_responses = max(total_responses, question_stats['total'])
            
            for answer in answers:
                if question.question_type in ['RADIO', 'CHECKBOX', 'SELECT_SINGLE', 'SELECT_MULTIPLE']:
                    # For RADIO and CHECKBOX with selected_choices
                    if answer.selected_choices.exists():
                        for choice in answer.selected_choices.all():
                            question_stats['answers'][choice.choice_text] += 1
                    # For SELECT_SINGLE and SELECT_MULTIPLE with text_answer
                    elif answer.text_answer:
                        if question.question_type in ['SELECT_SINGLE', 'SELECT_MULTIPLE']:
                            # Handle comma-separated values for multiple selection
                            if question.question_type == 'SELECT_MULTIPLE':
                                selected = [item.strip() for item in answer.text_answer.split(',')]
                                for item in selected:
                                    # Try to find choice by ID first, otherwise use the text
                                    choice = question.choices.filter(id=item).first()
                                    if choice:
                                        question_stats['answers'][choice.choice_text] += 1
                                    else:
                                        question_stats['answers'][item] += 1
                            else:  # SELECT_SINGLE
                                choice = question.choices.filter(id=answer.text_answer).first()
                                if choice:
                                    question_stats['answers'][choice.choice_text] += 1
                                else:
                                    question_stats['answers'][answer.text_answer] += 1
                        elif question.question_type in ['RADIO', 'CHECKBOX']:
                            # For RADIO and CHECKBOX without selected_choices, use text_answer
                            if question.question_type == 'RADIO':
                                question_stats['answers'][answer.text_answer] += 1
                            else:  # CHECKBOX
                                # Handle comma-separated values for checkbox
                                selected = [item.strip() for item in answer.text_answer.split(',')]
                                for item in selected:
                                    question_stats['answers'][item] += 1
                elif question.question_type in ['TEXT', 'TEXT_SHORT', 'TEXTAREA']:
                    question_stats['answers']['Текстовые ответы'] += 1
                elif question.question_type == 'PHOTO':
                    question_stats['answers']['Фотоответы'] += 1
            
            stats[str(question.id)] = question_stats
        
        return stats, total_responses
    
    @staticmethod
    def generate_photo_statistics(task):
        """Generate statistics for photo report tasks."""
        reports = PhotoReport.objects.filter(task=task)
        total_responses = reports.count()
        return {}, total_responses
    
    @classmethod
    def generate_all_statistics(cls):
        """Generate statistics for all tasks."""
        tasks = Task.objects.filter(status='COMPLETED')
        
        for task in tasks:
            if task.task_type == 'SURVEY':
                survey_stats, total_responses = cls.generate_survey_statistics(task)
                completed_tasks = 1 if total_responses > 0 else 0
            else:
                survey_stats, total_responses = cls.generate_photo_statistics(task)
                completed_tasks = 1 if total_responses > 0 else 0
            
            # Update or create statistics record
            TaskStatistics.objects.update_or_create(
                task=task,
                client=task.client,
                employee=task.assigned_to,
                moderator=task.created_by,
                defaults={
                    'total_responses': total_responses,
                    'completed_tasks': completed_tasks,
                    'pending_tasks': 0,
                    'survey_stats': survey_stats
                }
            )