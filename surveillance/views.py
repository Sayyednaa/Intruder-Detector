import io, time, base64
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django import forms
import numpy as np
import cv2
import qrcode
from django.views.decorators.csrf import csrf_protect
from .models import Device, IntrusionEvent, LastFrame
from .forms import DeviceForm
from .utils import detect_motion, detect_person

# ----------------- Device Views -----------------

def monitor(request):
    if request.user.is_authenticated:
        
        devices = Device.objects.filter(user=request.user).order_by('-last_seen')
        return render(request, 'surveillance/monitor.html', {'devices': devices})
    else:
        return redirect('login')


def devices(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if request.method == 'POST':
        form = DeviceForm(request.POST)
        if form.is_valid():
            dev = form.save(commit=False)
            dev.user = request.user
            dev.save()
            LastFrame.objects.get_or_create(device=dev, defaults={'user': request.user})
            return redirect('device_detail', pk=dev.pk)
    else:
        form = DeviceForm()
    user_devices = Device.objects.filter(user=request.user).order_by('-id')
    return render(request, 'surveillance/devices.html', {'form': form, 'devices': user_devices})

def device_detail(request, pk):
    if not request.user.is_authenticated:
        return redirect('login')
    dev = get_object_or_404(Device, pk=pk, user=request.user)
    events = IntrusionEvent.objects.filter(device=dev, user=request.user).order_by('-timestamp')[:100]
    return render(request, 'surveillance/device_detail.html', {'dev': dev, 'events': events})

def client_page(request):
    if not request.user.is_authenticated:
        return redirect('login')
    token = request.GET.get('token')
    if not token:
        return HttpResponseBadRequest('Missing ?token=')
    dev = get_object_or_404(Device, token=token, is_active=True, user=request.user)
    return render(request, 'surveillance/client.html', {'device': dev})

def pair_qr(request, pk):
    if not request.user.is_authenticated:
        return redirect('login')
    dev = get_object_or_404(Device, pk=pk, user=request.user)
    url = request.build_absolute_uri(f"/client/?token={dev.token}")
    img = qrcode.make(url)
    bio = io.BytesIO()
    img.save(bio, format='PNG')
    bio.seek(0)
    return FileResponse(bio, content_type='image/png')

# ----------------- Frame Upload -----------------

@csrf_exempt
def upload_frame(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if request.method != 'POST':
        return HttpResponseBadRequest('POST only')
    token = request.GET.get('token') or request.POST.get('token')
    if not token:
        return HttpResponseBadRequest('Missing token')
    
    try:
        dev = Device.objects.get(token=token, is_active=True, user=request.user)
    except Device.DoesNotExist:
        return HttpResponseBadRequest('Invalid token')

    frame_bytes = None
    if 'frame' in request.FILES:
        frame_bytes = request.FILES['frame'].read()
    else:
        b64 = request.POST.get('frame_b64')
        if b64 and b64.startswith('data:image/jpeg;base64,'):
            b64 = b64.split(',',1)[1]
        if b64:
            frame_bytes = base64.b64decode(b64)
    if not frame_bytes:
        return HttpResponseBadRequest('No frame')

    dev.last_seen = timezone.now()
    dev.save(update_fields=['last_seen'])

    np_arr = np.frombuffer(frame_bytes, np.uint8)
    frame_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if frame_bgr is None:
        return HttpResponseBadRequest('Bad image')

    motion_score, _ = detect_motion(token, frame_bgr, dev.motion_sensitivity)
    motion_triggered = motion_score > dev.motion_sensitivity

    person_triggered, person_score = (False, 0.0)
    if motion_triggered:
        person_triggered, person_score = detect_person(frame_bgr)

    ok, jpg = cv2.imencode('.jpg', frame_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
    if ok:
        jf = ContentFile(jpg.tobytes(), name=f"{token}.jpg")
        lf, _ = LastFrame.objects.get_or_create(device=dev, defaults={'user': request.user})
        lf.frame.save(f"{token}.jpg", jf, save=False)
        lf.width, lf.height = frame_bgr.shape[1], frame_bgr.shape[0]

        now = timezone.now()
        if lf.pk and lf.updated_at:
            dt = (now - lf.updated_at).total_seconds() or 1.0
            lf.fps = max(0.1, min(30.0, 1.0/dt))

        lf.save()

    event = None
    if motion_triggered or person_triggered:
        kind = 'human' if person_triggered else 'motion'
        score = float(person_score if person_triggered else motion_score)
        ok, snap = cv2.imencode('.jpg', frame_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        if ok:
            snap_content = ContentFile(snap.tobytes(), name=f"{token}_{int(time.time())}.jpg")
            event = IntrusionEvent.objects.create(device=dev, snapshot=snap_content, kind=kind, score=score, user=request.user)

    return JsonResponse({
        'ok': True,
        'motion_score': round(float(motion_score), 4),
        'person': bool(person_triggered),
        'person_score': round(float(person_score), 4),
        'intrusion_saved': bool(event),
    })

def last_frame_jpg(request, token):
    if not request.user.is_authenticated:
        return redirect('login')
    try:
        dev = Device.objects.get(token=token, user=request.user)
        lf = LastFrame.objects.get(device=dev, user=request.user)
    except (Device.DoesNotExist, LastFrame.DoesNotExist):
        return HttpResponse(status=404)
    with open(lf.frame.path, 'rb') as f:
        data = f.read()
    return HttpResponse(data, content_type='image/jpeg')

def events(request):
    if not request.user.is_authenticated:
        return redirect('login')
    qs = IntrusionEvent.objects.filter(user=request.user).select_related('device').order_by('-timestamp')
    paginator = Paginator(qs, 40)
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)
    return render(request, 'surveillance/events.html', {'events': page_obj.object_list})

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('monitor')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not username or not email or not password or not confirm_password:
            messages.error(request, "All fields are required.")
        elif password != confirm_password:
            messages.error(request, "Passwords do not match.")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
        else:
            user = User.objects.create_user(username=username, email=email, password=password)
            login(request, user)
            return redirect('monitor')

    return render(request, 'surveillance/signup.html')

# ----------------- Login -----------------
def login_view(request):
   
    if request.user.is_authenticated:
        return redirect('monitor')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        if not username or not password:
            messages.error(request, "Both fields are required.")
        else:
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                return redirect('monitor')
            else:
                messages.error(request, "Invalid username or password.")

    return render(request, 'surveillance/login.html')

# ----------------- Logout -----------------
def logout_view(request):
    logout(request)
    return redirect('login')





# Delete a captured intrusion

def delete_all_data(request):
    if request.method == 'POST':
        # Delete all intrusion snapshots
        intrusions = IntrusionEvent.objects.filter(user=request.user)
        for e in intrusions:
            if e.snapshot:
                e.snapshot.delete(save=False)
        intrusions.delete()

        # Delete all last frames
        frames = LastFrame.objects.filter(user=request.user)
        for f in frames:
            if f.frame:
                f.frame.delete(save=False)
        frames.delete()

        messages.success(request, "All intrusions and frames deleted successfully.")
        return redirect(request.META.get('HTTP_REFERER', 'monitor'))
    else:
        messages.warning(request, "Invalid request.")
        return redirect('monitor')




def delete_device(request, pk):
    dev = get_object_or_404(Device, pk=pk, user=request.user)

    # Delete all intrusions for this device
    intrusions = IntrusionEvent.objects.filter(device=dev, user=request.user)
    for e in intrusions:
        if e.snapshot:
            e.snapshot.delete(save=False)
    intrusions.delete()

    # Delete last frame
    try:
        lf = LastFrame.objects.get(device=dev, user=request.user)
        if lf.frame:
            lf.frame.delete(save=False)
        lf.delete()
    except LastFrame.DoesNotExist:
        pass

    # Finally delete the device
    dev.delete()

    messages.success(request, f"Device '{dev.name}' and all its data deleted successfully.")
    return redirect(request.META.get('HTTP_REFERER', 'devices'))