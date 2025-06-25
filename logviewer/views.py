from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from .models import LogEntry, TestStation
import json

def logs_list(request):
    """Display all logs with filtering and pagination"""
    
    # Get filter parameters
    station_filter = request.GET.get('station', '')
    result_filter = request.GET.get('result', '')
    search_query = request.GET.get('search', '')
    
    # Start with all logs, ordered by most recent
    logs = LogEntry.objects.all().order_by('-timestamp')
    
    # Apply filters
    if station_filter:
        logs = logs.filter(station_id=station_filter)
    
    if result_filter:
        logs = logs.filter(result=result_filter)
    
    if search_query:
        logs = logs.filter(
            Q(station_id__icontains=search_query) |
            Q(filename__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(logs, 25)  # 25 logs per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get unique stations for filter dropdown (simple approach)
    all_logs = LogEntry.objects.all()
    stations = list(set(log.station_id for log in all_logs))
    stations.sort()
    
    # Statistics (calculate from all logs, not filtered)
    total_logs = all_logs.count()
    pass_count = len([log for log in all_logs if log.result == 'PASS'])
    fail_count = len([log for log in all_logs if log.result == 'FAIL'])
    
    context = {
        'page_obj': page_obj,
        'stations': stations,
        'current_station': station_filter,
        'current_result': result_filter,
        'search_query': search_query,
        'total_logs': total_logs,
        'pass_count': pass_count,
        'fail_count': fail_count,
        'pass_rate': round((pass_count / total_logs * 100) if total_logs > 0 else 0, 1)
    }
    
    return render(request, 'logviewer/logs.html', context)

def log_detail(request, log_id):
    """Display detailed view of a single log"""
    log = get_object_or_404(LogEntry, id=log_id)
    
    # Format metrics JSON for better display
    formatted_metrics = json.dumps(log.metrics, indent=2)
    
    context = {
        'log': log,
        'formatted_metrics': formatted_metrics,
    }
    
    return render(request, 'logviewer/log_detail.html', context)

def dashboard(request):
    """Dashboard with statistics and charts"""
    
    # Recent logs (last 10)
    recent_logs = LogEntry.objects.order_by('-timestamp')[:10]
    
    # Get all logs for manual processing (works better with MongoDB)
    all_logs = list(LogEntry.objects.all())
    
    # Calculate statistics manually
    total_logs = len(all_logs)
    pass_count = len([log for log in all_logs if log.result == 'PASS'])
    fail_count = len([log for log in all_logs if log.result == 'FAIL'])
    
    # Get unique stations and their stats
    station_data = {}
    for log in all_logs:
        station_id = log.station_id
        if station_id not in station_data:
            station_data[station_id] = {'total': 0, 'passes': 0, 'fails': 0}
        
        station_data[station_id]['total'] += 1
        if log.result == 'PASS':
            station_data[station_id]['passes'] += 1
        else:
            station_data[station_id]['fails'] += 1
    
    # Convert to list and add pass rates
    station_stats = []
    for station_id, stats in station_data.items():
        pass_rate = round((stats['passes'] / stats['total'] * 100) if stats['total'] > 0 else 0, 1)
        station_stats.append({
            'station_id': station_id,
            'total': stats['total'],
            'passes': stats['passes'],
            'fails': stats['fails'],
            'pass_rate': pass_rate
        })
    
    # Sort by total logs descending
    station_stats.sort(key=lambda x: x['total'], reverse=True)
    
    context = {
        'recent_logs': recent_logs,
        'station_stats': station_stats,
        'total_logs': total_logs,
        'total_stations': len(station_data),
        'pass_count': pass_count,
        'fail_count': fail_count,
        'overall_pass_rate': round((pass_count / total_logs * 100) if total_logs > 0 else 0, 1)
    }
    
    return render(request, 'logviewer/dashboard.html', context)