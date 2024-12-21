from django.shortcuts import render, redirect,get_object_or_404
from django.views.generic.base import TemplateView
from .forms import StaffForm, StaffWorkForm, CustomerForm, CustomerWorkForm, CalendarForm, OutputForm,PlaceRemarksForm
from .models import CustomerModel,CustomerWorkModel,StaffModel,StaffWorkModel, WorkPlaceModel,TransportMeansEnum,LunchEnum, StaffWorkStatusEnum, CustomerWorkStatusEnum, WORK_SESSION_COUNT, CurrentStatusEnum,PlaceRemarksModel
from datetime import datetime
from django.contrib.auth.decorators import login_required
from dateutil.relativedelta import relativedelta
from django.http import HttpResponse
import csv
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash

class IndexView(TemplateView):
    template_name = 'app/index.html'

def info_today(request):
    work_date = datetime.now().date()

    return redirect('info', work_date)

def info(request, work_date):

    calendar_form = CalendarForm(initial_date=work_date)

    staff_work_exists = StaffWorkModel.objects.filter(work_date=work_date).exists()
    customer_work_exists = CustomerWorkModel.objects.filter(work_date=work_date).exists()

    if not staff_work_exists and not customer_work_exists:
        # 両方のデータが存在しない場合の処理
        return render(request, 'app/info_no_data.html', {
            'work_date': work_date,
            'calendar_form':calendar_form,
            })

    lunch_info = create_info_by_lunch(work_date)

    info_by_place = create_info_by_place(work_date)

    info_by_staff = create_info_by_staff(work_date)

    info_by_customer = create_info_by_customer(work_date)

    return render(request,'app/info.html',{
        'work_date':work_date,
        'calendar_form':calendar_form,
        'lunch_info':lunch_info,
        'info_by_place': info_by_place,
        'info_by_staff':info_by_staff,
        'info_by_customer':info_by_customer,
        })

def create_info_by_lunch(work_date):
    work_places = WorkPlaceModel.objects.all()

    total_lunch_count_staff = 0
    total_lunch_count_customer = 0

    lunch_by_area = {}
    
    staff_works = StaffWorkModel.objects.filter(work_date=work_date).order_by('staff__order')
    customer_works = CustomerWorkModel.objects.filter(work_date=work_date).order_by('customer__order')

    for work_place in work_places:

        lunch_count_staff = sum(
        1 for staff_work in staff_works
        for i in range(1, WORK_SESSION_COUNT + 1)
        if getattr(staff_work, f'work{i}_place') == work_place and staff_work.lunch == LunchEnum.ORDERED_LUNCH_BOX.value and staff_work.eat_lunch_at == i
        )

        lunch_count_customer = sum(
            1 for customer_work in customer_works
            for i in range(1, WORK_SESSION_COUNT + 1)
            if getattr(customer_work, f'work{i}_place') == work_place and customer_work.lunch == LunchEnum.ORDERED_LUNCH_BOX.value and customer_work.eat_lunch_at == i
        )

        total_lunch_count_staff += lunch_count_staff
        total_lunch_count_customer += lunch_count_customer

        area = work_place.area
        if area not in lunch_by_area:
            lunch_by_area[area] = {
                'count': 0,
                'name': [],
            }

        lunch_by_area[area]['count'] += lunch_count_staff + lunch_count_customer
        
        # スタッフの名前を追加
        lunch_by_area[area]['name'].extend(
            staff_work.staff_name for staff_work in staff_works
            for i in range(1, WORK_SESSION_COUNT + 1)
            if staff_work.eat_lunch_at == i and getattr(staff_work, f'work{i}_place') == work_place and staff_work.lunch == LunchEnum.ORDERED_LUNCH_BOX.value
        )

    for work_place in work_places:
        # 利用者の名前を追加(スタッフのあとに利用者を追加)
        area = work_place.area
        lunch_by_area[area]['name'].extend(
            customer_work.customer_name for customer_work in customer_works
            for i in range(1, WORK_SESSION_COUNT + 1)
            if customer_work.eat_lunch_at == i and getattr(customer_work, f'work{i}_place') == work_place and customer_work.lunch == LunchEnum.ORDERED_LUNCH_BOX.value
        )   

    lunch_info = {
        'total_count': total_lunch_count_staff + total_lunch_count_customer,
        'staff_count': total_lunch_count_staff,
        'customer_count': total_lunch_count_customer,
        'by_area': lunch_by_area,
    } 

    return lunch_info

def create_info_by_place(work_date):

    staff_works = StaffWorkModel.objects.filter(work_date=work_date).order_by('staff__order')
    customer_works = CustomerWorkModel.objects.filter(work_date=work_date).order_by('customer__order')

    work_places = WorkPlaceModel.objects.all()

    info_by_place = []

    for work_place in work_places:
        staff_list = [
            {
                'name':staff_work.staff_name,
                'time':(
                    f"{getattr(staff_work, f'work{i}_start_time').strftime('%H:%M')}～{getattr(staff_work, f'work{i}_end_time').strftime('%H:%M')}"
                    if getattr(staff_work, f'work{i}_start_time') and getattr(staff_work, f'work{i}_end_time')
                    else ""
                ),          
                'eats_lunch_here': (
                    "注文" if staff_work.lunch == LunchEnum.ORDERED_LUNCH_BOX.value else
                    "持参" if staff_work.lunch == LunchEnum.BYO_LUNCH_BOX.value else
                    ""
                ) if staff_work.eat_lunch_at == i else ""
            }
            for staff_work in staff_works
            for i in range(1, WORK_SESSION_COUNT + 1)
            if getattr(staff_work, f'work{i}_place') == work_place
        ]

        customer_list = [
            {
                'name':customer_work.customer_name,
                'time':(
                    f"{getattr(customer_work, f'work{i}_start_time').strftime('%H:%M')}～{getattr(customer_work, f'work{i}_end_time').strftime('%H:%M')}"
                    if getattr(customer_work, f'work{i}_start_time') and getattr(customer_work, f'work{i}_end_time')
                    else ""
                ),          
                'eats_lunch_here': (
                    "注文" if customer_work.lunch == LunchEnum.ORDERED_LUNCH_BOX.value else
                    "持参" if customer_work.lunch == LunchEnum.BYO_LUNCH_BOX.value else
                    ""
                ) if customer_work.eat_lunch_at == i else ""
            }
            for customer_work in customer_works
            for i in range(1, WORK_SESSION_COUNT + 1)
            if getattr(customer_work, f'work{i}_place') == work_place
        ]

        staff_customer_list = []
        max_length = max(len(staff_list), len(customer_list))

        for i in range(max_length):
            staff = staff_list[i] if i < len(staff_list) else None
            customer = customer_list[i] if i < len(customer_list) else None
            staff_customer_list.append((staff, customer))

        remarks = PlaceRemarksModel.objects.filter(place = work_place, work_date=work_date).first()

        if not remarks:
            remarks = PlaceRemarksModel(place = work_place, work_date=work_date)
            remarks.remarks="　"

        info_by_place.append({
            'work_place': work_place,
            'staff_cusotmer_list': staff_customer_list,
            'remarks': remarks.remarks,
        })

    return info_by_place

def create_info_by_staff(work_date):

    staffs = StaffModel.objects.all().order_by('order')
    customer_works = CustomerWorkModel.objects.filter(work_date=work_date).order_by('customer__order')
    
    info_by_staff = []

    for staff in staffs:
        staff_work = StaffWorkModel.objects.filter(staff_id=staff.pk, work_date=work_date).first()
            
        if not staff_work:
            staff_work = StaffWorkModel(staff=staff, work_date=work_date)
            staff_work.staff_name = staff.name

        places_and_times = []
        pickup_list = []
        dropoff_list = []
        lunch = ""

        if staff_work.work_status == StaffWorkStatusEnum.ON.value:

            # 勤務地&勤務時間のリスト
            for i in range(1,5):
                place = getattr(staff_work, f'work{i}_place', None)
                start_time = getattr(staff_work, f'work{i}_start_time', None)
                end_time = getattr(staff_work, f'work{i}_end_time', None)
                if place:
                    time = f"{start_time.strftime('%H:%M')}～{end_time.strftime('%H:%M')}" if start_time and end_time else ""
                    places_and_times.append({
                        'place': place.name,
                        'time': time
                    })

            # 朝の送迎リスト
            pickup_customers = [customer_work for customer_work in customer_works if customer_work.pickup_staff == staff_work.staff]
            
            for customer in pickup_customers:
                time_info = f"{customer.pickup_time.strftime('%H:%M')}" if customer.pickup_time else ""
                car_info = f"{customer.pickup_car}" if customer.pickup_car else ""

                pickup_list.append({
                    'name':customer.customer.name,
                    'time': time_info,
                    'car': car_info,
                })
                        
            # 帰りの送迎リスト
            dropoff_customers = [customer_work for customer_work in customer_works if customer_work.dropoff_staff == staff_work.staff]
            
            for customer in dropoff_customers:
                time_info = f"{customer.dropoff_time.strftime('%H:%M')}" if customer.dropoff_time else ""
                car_info = f"{customer.dropoff_car}" if customer.dropoff_car else ""

                dropoff_list.append({
                    'name':customer.customer.name,
                    'time': time_info,
                    'car': car_info,
                })

            lunch = staff_work.get_lunch_display()
        
        info_by_staff.append({
            'id':staff_work.staff.pk,
            'name':staff_work.staff_name,
            'status':staff_work.get_work_status_display(),
            'places_and_times':places_and_times,
            'pickup_list':pickup_list,
            'dropoff_list':dropoff_list,
            'lunch':lunch,
        })
            
    return info_by_staff

def create_info_by_customer(work_date):

    customers = CustomerModel.objects.all().order_by('order')

    info_by_customer = []

    for customer in customers:
        customer_work = CustomerWorkModel.objects.filter(customer=customer,work_date=work_date).first()

        if not customer_work:
            customer_work = CustomerWorkModel(customer=customer, work_date=work_date)
            customer_work.customer_name=customer.name

        places_and_times = []
        morning_transport = ""
        return_transport = ""
        current_status = ""
        lunch = ""

        if customer_work.work_status == CustomerWorkStatusEnum.OFFICE.value:

            current_status = customer_work.get_current_status_display()

            for i in range(1,WORK_SESSION_COUNT+1):
                place = getattr(customer_work, f'work{i}_place', None)
                start_time = getattr(customer_work, f'work{i}_start_time', None)
                end_time = getattr(customer_work, f'work{i}_end_time', None)

                if place:
                    time = f"{start_time.strftime('%H:%M')}～{end_time.strftime('%H:%M')}" if start_time and end_time else ""
                    places_and_times.append({
                        'place': place.name,
                        'time': time
                    })

            morning_transport = customer_work.get_morning_transport_display()
            if customer_work.morning_transport_means == TransportMeansEnum.TRANSFER.value:
                
                if customer_work.pickup_staff:
                    morning_transport +=f"\n{customer_work.pickup_staff}"

                if customer_work.pickup_place:
                    morning_transport +=f"\n{customer_work.pickup_place}"

                if customer_work.pickup_car:
                    morning_transport +=f"\n{customer_work.pickup_car}"

                if customer_work.pickup_time:
                    morning_transport +=f"\n{customer_work.pickup_time.strftime('%H:%M')}"

            return_transport = customer_work.get_return_transport_display()
            if customer_work.return_transport_means == TransportMeansEnum.TRANSFER.value:
                
                if customer_work.dropoff_staff:
                    return_transport +=f"\n{customer_work.dropoff_staff}"

                if customer_work.dropoff_place:
                    return_transport +=f"\n{customer_work.dropoff_place}"

                if customer_work.dropoff_car:
                    return_transport +=f"\n{customer_work.dropoff_car}"

                if customer_work.dropoff_time:
                    return_transport +=f"\n{customer_work.dropoff_time.strftime('%H:%M')}"
                

            lunch = customer_work.get_lunch_display()

        info_by_customer.append({
            'id':customer_work.customer.pk,
            'name':customer_work.customer_name,
            'status':customer_work.get_work_status_display(),
            'current_status':current_status,
            'places_and_times':places_and_times,
            'morning_transport':morning_transport,
            'return_transport':return_transport,
            'lunch':lunch
        })
    return info_by_customer

def info_dispatch(request, work_date):
    assert request.method == 'POST'
    change_date = request.POST.get('change_date')
    create_data = request.POST.get('create_data')
    edit_place_remarks = request.POST.get('edit_place_remarks')
    prev_status = request.POST.get('prev_status')
    next_status = request.POST.get('next_status')
    edit_customer = request.POST.get('edit_customer')
    edit_staff = request.POST.get('edit_staff')
   
    if change_date:
        work_date = request.POST.get('date')
        return redirect('info', work_date)
    elif create_data:
        work_date = request.POST.get('date')
        create_work_data(work_date)
        return redirect('info', work_date)
    elif edit_place_remarks:
        place_id = edit_place_remarks
        return redirect('place_remarks', place_id, work_date)
    elif prev_status:
        customer_id = prev_status
        to_prev_status(customer_id, work_date)
        return redirect('info', work_date)
    elif next_status:
        customer_id = next_status
        to_next_status(customer_id, work_date)
        return redirect('info', work_date)  
    elif edit_customer:
        customer_id = edit_customer
        return redirect('customer_date_work', 
        customer_id=customer_id, work_date=work_date)    
    elif edit_staff:
        staff_id = edit_staff
        return redirect('staff_date_work', 
        staff_id=staff_id, work_date=work_date)   
    
    return redirect('info', work_date)     

def to_prev_status(customer_id, work_date):
    customer_work = CustomerWorkModel.objects.filter(customer__pk=customer_id, work_date=work_date).first()

    if customer_work.current_status == CurrentStatusEnum.BEFORE_WORK.value:
        print("エラー:出勤前の状態で「前へ」ボタンが押されました")
        return
    if customer_work.current_status == CurrentStatusEnum.AFTER_WORK.value:

        for i in range(WORK_SESSION_COUNT,0,-1):
            place = getattr(customer_work, f'work{i}_place')
            if place:
                customer_work.current_status = i
                break
    else:
        customer_work.current_status -= 1

    customer_work.save()

def to_next_status(customer_id, work_date):
    customer_work = CustomerWorkModel.objects.filter(customer__pk=customer_id, work_date=work_date).first()

    if customer_work.current_status == CurrentStatusEnum.AFTER_WORK.value:
        print("エラー:退勤済みの状態で「次へ」ボタンが押されました")
        return
    if customer_work.current_status == WORK_SESSION_COUNT:
        customer_work.current_status = -1
    else:
        field_name = f"work{customer_work.current_status+1}_place"
        next_place = getattr(customer_work, field_name)
        if next_place:
            customer_work.current_status += 1
        else:
            customer_work.current_status = CurrentStatusEnum.AFTER_WORK.value

    customer_work.save()

def config_work(request, work_date):

    work_date_obj = datetime.strptime(work_date, '%Y-%m-%d').date()
    calendar_form = CalendarForm(initial_date=work_date_obj)

    staff_works = StaffWorkModel.objects.filter(work_date=work_date).order_by('staff__order')

    staff_list = []

    for staff_work in staff_works:
        staff_list.append({
            'id':staff_work.staff.pk,
            'name': staff_work.staff_name,
            'work_status': staff_work.get_work_status_display(),
            'work_places': [
                getattr(staff_work, f'work{i}_place') for i in range(1, WORK_SESSION_COUNT + 1)
                if getattr(staff_work, f'work{i}_place') 
            ],
        })

    customer_works = CustomerWorkModel.objects.filter(work_date=work_date).order_by('customer__order')

    customer_list = []

    for customer_work in customer_works:
        customer_list.append({
            'id':customer_work.customer.pk,
            'name': customer_work.customer_name,
            'work_status': customer_work.get_work_status_display(),
            'work_places': [
                getattr(customer_work, f'work{i}_place') for i in range(1, WORK_SESSION_COUNT + 1)
                if getattr(customer_work, f'work{i}_place') 
            ],
        })

    # StaffModelに存在し、StaffWorkModelに存在しないスタッフを取得
    staffs_with_work_entry = StaffWorkModel.objects.filter(work_date=work_date).values_list('staff', flat=True)
    staffs_without_work_entry = StaffModel.objects.exclude(id__in=staffs_with_work_entry).order_by('order')

    # CustomerModelに存在し、CustomerWorkModelに存在しないスタッフを取得
    customers_with_work_entry = CustomerWorkModel.objects.filter(work_date=work_date).values_list('customer', flat=True)
    customers_without_work_entry = CustomerModel.objects.exclude(id__in=customers_with_work_entry).order_by('order')
    
    return render(request,'app/config_work.html',{
        'calendar_form':calendar_form,
        'work_date':work_date,
        'staff_list':staff_list,
        'customer_list':customer_list,
        'staffs_without_work_entry':staffs_without_work_entry,
        'customers_without_work_entry':customers_without_work_entry,
        })

def create_work_data(work_date):
    staffs = StaffModel.objects.all().order_by('order')
    for staff in staffs:
        apply_pattern_to_staff(staff.pk, work_date)

    customers = CustomerModel.objects.all().order_by('order')
    for customer in customers:
        apply_pattern_to_customer(customer.pk, work_date)

    copyLastPlaceRemarks(work_date)

def create_staff_work_by_pattern(staff_id, work_date, work_status=None):
 
    staff = get_object_or_404(StaffModel, pk=staff_id)
    staff_work = StaffWorkModel(
        staff=staff, work_date=work_date, staff_name=staff.name
    )

    staff_work.staff_name = staff.name

    if work_status == StaffWorkStatusEnum.ON.value:
        staff_work.work_status = work_status
    else:
        # 曜日ごとのステータスを設定
        weekday_number = datetime.strptime(work_date, "%Y-%m-%d").date().weekday()
        if weekday_number == 0:
            staff_work.work_status = staff.work_status_mon
        elif weekday_number == 1:
            staff_work.work_status = staff.work_status_tue
        elif weekday_number == 2:
            staff_work.work_status = staff.work_status_wed        
        elif weekday_number == 3:
            staff_work.work_status = staff.work_status_thu
        elif weekday_number == 4:
            staff_work.work_status = staff.work_status_fri        
        elif weekday_number == 5:
            staff_work.work_status = staff.work_status_sat   
        elif weekday_number == 6:
            staff_work.work_status = staff.work_status_sun

    # ステータスが「OFFICE」の場合に詳細を設定
    if staff_work.work_status == StaffWorkStatusEnum.ON.value:
        staff_work.work1_start_time = staff.work1_start_time
        staff_work.work1_end_time = staff.work1_end_time
        staff_work.work1_place = staff.work1_place
        staff_work.work2_start_time = staff.work2_start_time
        staff_work.work2_end_time = staff.work2_end_time
        staff_work.work2_place = staff.work2_place
        staff_work.work3_start_time = staff.work3_start_time
        staff_work.work3_end_time = staff.work3_end_time
        staff_work.work3_place = staff.work3_place
        staff_work.work4_start_time = staff.work4_start_time
        staff_work.work4_end_time = staff.work4_end_time
        staff_work.work4_place = staff.work4_place
        staff_work.lunch = staff.lunch
        staff_work.eat_lunch_at = staff.eat_lunch_at

    return staff_work

def apply_pattern_to_staff(staff_id, work_date):
    staff_work = create_staff_work_by_pattern(staff_id, work_date)

    StaffWorkModel.objects.filter(staff_id=staff_id, work_date=work_date).delete()

    staff_work.save()

def create_customer_work_by_pattern(customer_id, work_date, work_status=None):
 
    customer = get_object_or_404(CustomerModel, pk=customer_id)
    customer_work = CustomerWorkModel(
        customer=customer, work_date=work_date, customer_name=customer.name
    )

    customer_work.customer_name = customer.name

    if work_status == CustomerWorkStatusEnum.OFFICE.value:
        customer_work.work_status = work_status
    else:
    # 曜日ごとのステータスを設定
        weekday_number = datetime.strptime(work_date, "%Y-%m-%d").date().weekday()
        if weekday_number == 0:
            customer_work.work_status = customer.work_status_mon
        elif weekday_number == 1:
            customer_work.work_status = customer.work_status_tue
        elif weekday_number == 2:
            customer_work.work_status = customer.work_status_wed        
        elif weekday_number == 3:
            customer_work.work_status = customer.work_status_thu
        elif weekday_number == 4:
            customer_work.work_status = customer.work_status_fri        
        elif weekday_number == 5:
            customer_work.work_status = customer.work_status_sat   
        elif weekday_number == 6:
            customer_work.work_status = customer.work_status_sun

    # ステータスが「OFFICE」の場合に詳細を設定
    if customer_work.work_status == CustomerWorkStatusEnum.OFFICE.value:
        customer_work.morning_transport_means=customer.morning_transport_means
        customer_work.pickup_place=customer.pickup_place
        customer_work.pickup_staff=customer.pickup_staff
        customer_work.pickup_time=customer.pickup_time
        customer_work.return_transport_means=customer.return_transport_means
        customer_work.dropoff_place=customer.dropoff_place
        customer_work.dropoff_staff=customer.dropoff_staff
        customer_work.dropoff_time=customer.dropoff_time
        customer_work.dropoff_car=customer.dropoff_car
        customer_work.work1_start_time = customer.work1_start_time
        customer_work.work1_end_time = customer.work1_end_time
        customer_work.work1_place = customer.work1_place
        customer_work.work2_start_time = customer.work2_start_time
        customer_work.work2_end_time = customer.work2_end_time
        customer_work.work2_place = customer.work2_place
        customer_work.work3_start_time = customer.work3_start_time
        customer_work.work3_end_time = customer.work3_end_time
        customer_work.work3_place = customer.work3_place
        customer_work.work4_start_time = customer.work4_start_time
        customer_work.work4_end_time = customer.work4_end_time
        customer_work.work4_place = customer.work4_place
        customer_work.lunch = customer.lunch
        customer_work.eat_lunch_at = customer.eat_lunch_at

    return customer_work

def apply_pattern_to_customer(customer_id, work_date):
    customer_work = create_customer_work_by_pattern(customer_id, work_date)

    CustomerWorkModel.objects.filter(customer_id=customer_id, work_date=work_date).delete()

    customer_work.save()

def copyLastPlaceRemarks(work_date):

    all_places = WorkPlaceModel.objects.all()
    
    for place in all_places:
        latest_place_remarks = PlaceRemarksModel.objects.filter(place=place, work_date__lt=work_date).order_by('-work_date').first()

        if latest_place_remarks:
            # 最新のデータをコピー
            new_place_remarks = PlaceRemarksModel(
                place=place,
                work_date=work_date,
                remarks=latest_place_remarks.remarks,
            )
            # 新しいデータを保存
            new_place_remarks.save()


def staff_date_work(request, staff_id, work_date):
    
    staff = get_object_or_404(StaffModel, pk=staff_id)

    staff_work = StaffWorkModel.objects.filter(staff=staff, work_date=work_date).first()
    
    if not staff_work:
        staff_work = create_staff_work_by_pattern(staff_id=staff.pk, work_date=work_date)

    form = StaffWorkForm(instance = staff_work)

    return render(request, 'app/staff_date_work.html', {
        'form': form,
        'staff_id': staff_id,
        'staff_name':staff.name,
        'work_date': work_date,
    })  

def config_work_update_staff(request, staff_id, work_date):     
    assert request.method == 'POST'

    action = request.POST.get('action')

    if action == 'pattern':
        staff = get_object_or_404(StaffModel, pk=staff_id)

        staff_work = create_staff_work_by_pattern(
            staff_id=staff_id, 
            work_date=work_date, 
            work_status = StaffWorkStatusEnum.ON.value
            )

        form = StaffWorkForm(instance = staff_work)

        return render(request, 'app/staff_date_work.html', {
                'form': form,
                'staff_id': staff_id,
                'staff_name':staff.name,
                'work_date': work_date,
            })
    
    elif action == 'save':
        staff = get_object_or_404(StaffModel, pk=staff_id)

        staff_work, created = StaffWorkModel.objects.get_or_create(staff=staff, work_date=work_date)

        form = StaffWorkForm(request.POST, instance=staff_work)

        if form.is_valid():
            StaffWorkModel.objects.filter(staff_id=staff_id, work_date=work_date).delete()
            staff_work = form.save(commit=False)  # まずはコミットせずにインスタンスを取得
            staff_work.work_date = work_date  # work_dateを設定
            staff_work.save()  # インスタンスを保存
            return redirect('info', work_date)
        else:
            # フォームが無効な場合、エラーメッセージと共に再レンダリング
            print("エラー内容:", form.errors)
            return render(request, 'app/staff_date_work.html', {
                'form': form,
                'staff_id': staff_id,
                'staff_name':staff.name,
                'work_date': work_date,
            })
    else: # cancel
        return redirect('info', work_date)
       
def customer_date_work(request, customer_id, work_date):

    customer = get_object_or_404(CustomerModel, pk=customer_id)

    customer_work = CustomerWorkModel.objects.filter(customer=customer, work_date=work_date).first()

    if not customer_work:
        customer_work = create_customer_work_by_pattern(customer_id=customer_id, work_date=work_date)

    form = CustomerWorkForm(instance = customer_work)

    return render(request, 'app/customer_date_work.html', {
            'form': form,
            'customer_id': customer_id,
            'customer_name':customer.name,
            'work_date': work_date,
        })

def config_work_update_customer(request, customer_id, work_date):     
    assert request.method == 'POST'

    action = request.POST.get('action')

    if action == 'pattern':
        customer = get_object_or_404(CustomerModel, pk=customer_id)

        customer_work = create_customer_work_by_pattern(
            customer_id = customer_id, 
            work_date = work_date,
            work_status = CustomerWorkStatusEnum.OFFICE.value
            )

        form = CustomerWorkForm(instance = customer_work)

        return render(request, 'app/customer_date_work.html', {
                'form': form,
                'customer_id': customer_id,
                'customer_name':customer.name,
                'work_date': work_date,
            })
        
    elif action == 'save':
        customer = get_object_or_404(CustomerModel, pk=customer_id)

        customer_work, created = CustomerWorkModel.objects.get_or_create(customer=customer, work_date=work_date)

        form = CustomerWorkForm(request.POST, instance=customer_work)

        if form.is_valid():
            CustomerWorkModel.objects.filter(customer_id=customer_id, work_date=work_date).delete()
            customer_work = form.save(commit=False)  # まずはコミットせずにインスタンスを取得
            customer_work.work_date = work_date
            form.save()
            return redirect('info', work_date)
        else:
            # フォームが無効な場合、エラーメッセージと共に再レンダリング
            print("エラー内容:", form.errors)
            return render(request, 'app/customer_date_work.html', {
                'form': form,
                'customer_id': customer_id,
                'customer_name':customer.name,
                'work_date': work_date
            })
    else: # cancel
        return redirect('info', work_date)

def place_remarks(request, place_id, work_date):
    place = WorkPlaceModel.objects.get(pk=place_id)
    place_remarks = PlaceRemarksModel.objects.filter(place=place, work_date=work_date).first()
    if not place_remarks:
        place_remarks = PlaceRemarksModel(place=place,work_date=work_date)

    form = PlaceRemarksForm(instance=place_remarks)
    return render(request, 'app/place_remarks.html',{'form':form, 'place':place,'work_date':work_date,'place_remarks': place_remarks,})

def save_place_remarks(request, place_id, work_date):
    assert request.method == 'POST'    

    action = request.POST.get('action')

    place = get_object_or_404(WorkPlaceModel, pk=place_id)

    if action == 'save':
        place_remarks, created = PlaceRemarksModel.objects.get_or_create(
            place=place,
            work_date=work_date,
            defaults={'remarks': ''}
        )

        form = PlaceRemarksForm(request.POST, instance=place_remarks)
            
        if form.is_valid():
            place_remarks.save()
            
    elif action == 'cancel':
        ""# do nothing

    return redirect('info', work_date=work_date)

def staff(request):
    staffs = StaffModel.objects.all().order_by('order')
    return render(request, 'app/staff.html',{'staffs':staffs})

def config_staff_dispatch(request):
    assert request.method == 'POST'

    create = request.POST.get('create')
    up = request.POST.get('up')
    down = request.POST.get('down')
    update = request.POST.get('update')
    delete = request.POST.get('delete')
    
    if create:
        return redirect('config_staff_create')
    elif up:
        staff_id = up
        move_staff_up(staff_id)
        return redirect('staff')
    elif down:
        staff_id = down
        move_staff_down(staff_id)
        return redirect('staff')
    elif update:
        staff_id = update
        return redirect('config_staff_update', staff_id=staff_id)
    elif delete:
        staff_id = delete
        return redirect('config_staff_delete', staff_id=staff_id)
    return redirect('staff')

def move_staff_up(staff_id):
    staff = get_object_or_404(StaffModel, pk=staff_id)
    previous_staff = StaffModel.objects.filter(order__lt=staff.order).order_by('-order').first()
    if previous_staff:
        # 現在のスタッフと前のスタッフのorderを入れ替える
        staff.order, previous_staff.order = previous_staff.order, staff.order
        staff.save()
        previous_staff.save()

def move_staff_down(staff_id):
    staff = get_object_or_404(StaffModel, pk=staff_id)
    next_staff = StaffModel.objects.filter(order__gt=staff.order).order_by('order').first()
    if next_staff:
        # 現在のスタッフと次のスタッフのorderを入れ替える
        staff.order, next_staff.order = next_staff.order, staff.order
        staff.save()
        next_staff.save()

def config_staff_create(request):
    form = StaffForm()
    return render(request, 'app/staff_pattern.html', {'form': form, 'staff_id':0})

def config_staff_update(request,staff_id):
    staff = get_object_or_404(StaffModel, pk=staff_id)
    form = StaffForm(instance=staff)  
        
    return render(request, 'app/staff_pattern.html', {'form': form, 'staff_id':staff_id})

def config_staff_save(request, staff_id):
    assert request.method == 'POST'

    action = request.POST.get('action')

    if action == 'save':  
        print('save')  
        if staff_id == 0:
            form = StaffForm(request.POST) 
            template_name = 'config_staff_create'
        else:
            staff = StaffModel.objects.filter(pk=staff_id).first()
            form = StaffForm(request.POST, instance=staff) 
            template_name = 'config_staff_update'        

        if form.is_valid():
            form.save()
            return redirect('staff')
        else:
            return render(request, template_name, {'form': form, 'staff_id':staff_id})
    else: # cancel
        return redirect('staff')

def config_staff_delete(request, staff_id):
    staff = get_object_or_404(StaffModel, pk=staff_id)
    staff.delete()
    return redirect('staff')

def customer(request):
    customers = CustomerModel.objects.all().order_by('order')
    return render(request, 'app/customer.html',{'customers':customers})

def config_customer_dispatch(request):
    assert request.method == 'POST'

    create = request.POST.get('create')
    up = request.POST.get('up')
    down = request.POST.get('down')
    update = request.POST.get('update')
    delete = request.POST.get('delete')
    
    if create:
        return redirect('config_customer_create')
    elif up:
        customer_id = up
        move_customer_up(customer_id)
        return redirect('customer')
    elif down:
        customer_id = down
        move_customer_down(customer_id)
        return redirect('customer')
    elif update:
        customer_id = update
        return redirect('config_customer_update', customer_id=customer_id)
    elif delete:
        customer_id = delete
        return redirect('config_customer_delete', customer_id=customer_id)
    
    return redirect('customer')

def move_customer_up(customer_id):
    customer = get_object_or_404(CustomerModel, pk=customer_id)
    previous_customer = CustomerModel.objects.filter(order__lt=customer.order).order_by('-order').first()
    if previous_customer:
        # 現在の利用者と前の利用者のorderを入れ替える
        customer.order, previous_customer.order = previous_customer.order, customer.order
        customer.save()
        previous_customer.save()

def move_customer_down(customer_id):
    customer = get_object_or_404(CustomerModel, pk=customer_id)
    next_customer = CustomerModel.objects.filter(order__gt=customer.order).order_by('order').first()
    if next_customer:
        # 現在の利用者と次の利用者のorderを入れ替える
        customer.order, next_customer.order = next_customer.order, customer.order
        customer.save()
        next_customer.save()

def config_customer_create(request):
    form = CustomerForm()
    return render(request, 'app/customer_pattern.html', {'form': form, 'customer_id':0})

def config_customer_update(request,customer_id):
    customer = get_object_or_404(CustomerModel, pk=customer_id)
    form = CustomerForm(instance=customer)  
        
    return render(request, 'app/customer_pattern.html', {'form': form, 'customer_id':customer_id})

def config_customer_save(request, customer_id):
    assert request.method == 'POST'

    action = request.POST.get('action')

    if action == 'save':
        if customer_id == 0:
            form = CustomerForm(request.POST) 
            template_name = 'config_customer_create'
        else:
            customer = CustomerModel.objects.filter(pk=customer_id).first()
            form = CustomerForm(request.POST, instance=customer) 
            template_name = 'config_customer_update'        

        if form.is_valid():
            form.save()
            return redirect('customer')
        else:
            return render(request, template_name, {'form': form, 'customer_id':customer_id})
    else: # cancel
        return redirect('customer')

def config_customer_delete(request, customer_id):
    customer = get_object_or_404(CustomerModel, pk=customer_id)
    customer.delete()
    return redirect('customer')

def export(request):

    today = datetime.now().date()
    first_day_of_last_month = (today.replace(day=1) - relativedelta(months=1))
    start_date = CalendarForm(initial_date=first_day_of_last_month)
    end_date = CalendarForm(initial_date=today)

    form = OutputForm()

    return render(request,'app/export.html', {
        'start_date':start_date,
        'end_date':end_date,
        'form':form
        })

def export_execute(request):
    form = OutputForm(request.POST)

    dates = request.POST.getlist('date')
    start_date = dates[0]
    end_date = dates[1]

    if form.is_valid():
        target = form.cleaned_data['target']

        if target == 'customer':
            return exportCustomerWorkData(start_date, end_date)
        elif target == 'staff':
            return exportStaffWorkData(start_date, end_date)

def exportCustomerWorkData(start_date, end_date):

    queryset = CustomerWorkModel.objects.filter(work_date__range=[start_date, end_date]).order_by('customer_id', 'work_date')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="customer_work_data.csv"'

    response.write('\ufeff')

    writer = csv.writer(response)

    writer.writerow([
        '利用者名', '日付', '勤務種別', 
        '送迎(朝)', '送迎場所(朝)', '送迎スタッフ(朝)', '送迎時間(朝)', '送迎車(朝)', 
        '送迎(帰り)', '送迎場所(帰り)', '送迎スタッフ(帰り)', '送迎時間(帰り)', '送迎車(帰り)', 
        '昼食', 
        '勤務1(開始時間)','勤務1(終了時間)','勤務1(場所)'
        '勤務2(開始時間)','勤務2(終了時間)','勤務2(場所)'
        '勤務3(開始時間)','勤務3(終了時間)','勤務3(場所)'
        '勤務4(開始時間)','勤務4(終了時間)','勤務4(場所)'
    ])

    for record in queryset:
        writer.writerow([
            record.customer_name,
            record.work_date,
            record.get_work_status_display(), 
            record.get_morning_transport_display(), 
            record.pickup_place,
            record.pickup_staff.name if record.pickup_staff else '',
            record.pickup_time.strftime('%H:%M') if record.pickup_time else '',
            record.pickup_car.name if record.pickup_car else '',
            record.get_return_transport_display(),
            record.dropoff_place,
            record.dropoff_staff.name if record.dropoff_staff else '',  
            record.dropoff_time.strftime('%H:%M') if record.dropoff_time else '',
            record.dropoff_car.name if record.dropoff_car else '',
            record.get_lunch_display(),
            record.work1_start_time.strftime('%H:%M') if record.work1_start_time else '',
            record.work1_end_time.strftime('%H:%M') if record.work1_end_time else '',
            record.work1_place,
            record.work2_start_time.strftime('%H:%M') if record.work2_start_time else '',
            record.work2_end_time.strftime('%H:%M') if record.work2_end_time else '',
            record.work2_place,
            record.work3_start_time.strftime('%H:%M') if record.work3_start_time else '',
            record.work3_end_time.strftime('%H:%M') if record.work3_end_time else '',
            record.work3_place,
            record.work4_start_time.strftime('%H:%M') if record.work4_start_time else '',
            record.work4_end_time.strftime('%H:%M') if record.work4_end_time else '',
            record.work4_place,
        ])

    return response


def exportStaffWorkData(start_date, end_date):
    queryset = StaffWorkModel.objects.filter(work_date__range=[start_date, end_date]).order_by('staff_id', 'work_date')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="staff_work_data.csv"'

    response.write('\ufeff')

    writer = csv.writer(response)

    writer.writerow([
        'スタッフ名', '日付', '勤務種別',  
        '昼食', 
        '勤務1(開始時間)','勤務1(終了時間)','勤務1(場所)'
        '勤務2(開始時間)','勤務2(終了時間)','勤務2(場所)'
        '勤務3(開始時間)','勤務3(終了時間)','勤務3(場所)'
        '勤務4(開始時間)','勤務4(終了時間)','勤務4(場所)'
    ])

    for record in queryset:
        writer.writerow([
            record.staff_name,
            record.work_date,
            record.get_work_status_display(), 
            record.get_lunch_display(),
            record.work1_start_time.strftime('%H:%M') if record.work1_start_time else '',
            record.work1_end_time.strftime('%H:%M') if record.work1_end_time else '',
            record.work1_place,
            record.work2_start_time.strftime('%H:%M') if record.work2_start_time else '',
            record.work2_end_time.strftime('%H:%M') if record.work2_end_time else '',
            record.work2_place,
            record.work3_start_time.strftime('%H:%M') if record.work3_start_time else '',
            record.work3_end_time.strftime('%H:%M') if record.work3_end_time else '',
            record.work3_place,
            record.work4_start_time.strftime('%H:%M') if record.work4_start_time else '',
            record.work4_end_time.strftime('%H:%M') if record.work4_end_time else '',
            record.work4_place,
        ])

    return response

def password_change(request):
    user = request.user  # ログイン中のユーザーを取得
    if request.method == 'POST':
        form = PasswordChangeForm(user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # セッションを更新してログアウトを防ぐ
            return redirect('password_change_done')
    else:
        form = PasswordChangeForm(user)
    return render(request, 'app/password_change.html', {'form': form})

def history(request):
    return render(request, 'app/history.html')