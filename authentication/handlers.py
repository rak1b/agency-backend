from django.shortcuts import render


def handler403(request, exception):
    context = {}
    return render(request, 'error/403.html',context = context)


def handler404(request, exception):
    context = {}
    return render(request, 'error/404.html',context = context)


def handler500(request):
    context = {}
    return render(request, 'error/500.html',context = context)
