# forms.py
from django import forms
from .models import StaffModel, StaffWorkModel, CustomerModel, CustomerWorkModel, LunchEnum, CustomerWorkStatusEnum
import datetime

class StaffForm(forms.ModelForm):
    class Meta:
        model = StaffModel
        fields = [
            'name',
            'work_status_mon','work_status_tue','work_status_wed','work_status_thu','work_status_fri','work_status_sat','work_status_sun',
            'work1_start_time','work1_end_time','work1_place',
            'work2_start_time','work2_end_time','work2_place',
            'work3_start_time','work3_end_time','work3_place',
            'work4_start_time','work4_end_time','work4_place',
            'lunch',
            'eat_lunch_at',                             
            ]
        
        widgets = {  
            'work_status_mon':forms.Select,   
            'work_status_tue':forms.Select,
            'work_status_wed':forms.Select,
            'work_status_thu':forms.Select,   
            'work_status_fri':forms.Select,
            'work_status_sat':forms.Select,
            'work_status_sun':forms.Select,
            'work1_start_time':forms.TimeInput(attrs={'type': 'time'}),
            'work1_end_time':forms.TimeInput(attrs={'type': 'time'}),    
            'work1_place': forms.Select,  
            'work2_start_time':forms.TimeInput(attrs={'type': 'time'}),
            'work2_end_time':forms.TimeInput(attrs={'type': 'time'}),    
            'work2_place': forms.Select,          
            'work3_start_time':forms.TimeInput(attrs={'type': 'time'}),
            'work3_end_time':forms.TimeInput(attrs={'type': 'time'}),    
            'work3_place': forms.Select,   
            'work4_start_time':forms.TimeInput(attrs={'type': 'time'}),
            'work4_end_time':forms.TimeInput(attrs={'type': 'time'}),    
            'work4_place': forms.Select,
            'lunch': forms.Select,
            'eat_lunch_at': forms.RadioSelect                 
        }

class StaffWorkForm(forms.ModelForm):
    class Meta:
        model = StaffWorkModel
        fields = [
            'work_status',
            'work1_start_time','work1_end_time','work1_place',
            'work2_start_time','work2_end_time','work2_place',
            'work3_start_time','work3_end_time','work3_place',
            'work4_start_time','work4_end_time','work4_place',
            'lunch',
            'eat_lunch_at',
            ]
        
        widgets = {    
            'work_status':forms.Select,
            'work1_start_time':forms.TimeInput(attrs={'type': 'time'}),
            'work1_end_time':forms.TimeInput(attrs={'type': 'time'}),    
            'work1_place': forms.Select,  
            'work2_start_time':forms.TimeInput(attrs={'type': 'time'}),
            'work2_end_time':forms.TimeInput(attrs={'type': 'time'}),    
            'work2_place': forms.Select,          
            'work3_start_time':forms.TimeInput(attrs={'type': 'time'}),
            'work3_end_time':forms.TimeInput(attrs={'type': 'time'}),    
            'work3_place': forms.Select,   
            'work4_start_time':forms.TimeInput(attrs={'type': 'time'}),
            'work4_end_time':forms.TimeInput(attrs={'type': 'time'}),    
            'work4_place': forms.Select,
            'lunch': forms.Select,
            'eat_lunch_at': forms.RadioSelect                   
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['work_status'].choices = [
            choice for choice in self.fields['work_status'].choices if choice[0] != ''
        ]

class CustomerForm(forms.ModelForm):
    class Meta:
        model = CustomerModel
        fields = [
            'name',
            'morning_transport_means','pickup_place',
            'pickup_staff','pickup_time',
            'pickup_car',
            'return_transport_means','dropoff_place',
            'dropoff_staff','dropoff_time',
            'dropoff_car',        
            'work_status_mon', 'work_status_tue', 'work_status_wed', 'work_status_thu', 'work_status_fri', 'work_status_sat', 'work_status_sun', 
            'work1_start_time','work1_end_time','work1_place',
            'work2_start_time','work2_end_time','work2_place',
            'work3_start_time','work3_end_time','work3_place',
            'work4_start_time','work4_end_time','work4_place',
            'lunch',
            'eat_lunch_at',
            ]
        
        widgets = {
            'morning_transport_means': forms.Select,
            'pickup_time': forms.TimeInput(attrs={'type': 'time'}),
            'return_transport_means': forms.Select,
            'dropoff_time': forms.TimeInput(attrs={'type': 'time'}),           
            'work_status_mon':forms.Select,
            'work_status_tue':forms.Select,
            'work_status_wed':forms.Select,
            'work_status_thu':forms.Select,
            'work_status_fri':forms.Select,
            'work_status_sat':forms.Select,
            'work_status_sun':forms.Select,
            'work1_start_time':forms.TimeInput(attrs={'type': 'time'}),
            'work1_end_time':forms.TimeInput(attrs={'type': 'time'}),    
            'work1_place': forms.Select,  
            'work2_start_time':forms.TimeInput(attrs={'type': 'time'}),
            'work2_end_time':forms.TimeInput(attrs={'type': 'time'}),    
            'work2_place': forms.Select,          
            'work3_start_time':forms.TimeInput(attrs={'type': 'time'}),
            'work3_end_time':forms.TimeInput(attrs={'type': 'time'}),    
            'work3_place': forms.Select,   
            'work4_start_time':forms.TimeInput(attrs={'type': 'time'}),
            'work4_end_time':forms.TimeInput(attrs={'type': 'time'}),    
            'work4_place': forms.Select,
            'lunch': forms.Select,
            'eat_lunch_at': forms.RadioSelect               
        }

    pickup_staff = forms.ModelChoiceField(
        queryset=StaffModel.objects.all().order_by('order'),
        required=False,
    )

    dropoff_staff = forms.ModelChoiceField(
        queryset=StaffModel.objects.all().order_by('order'),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['work1_place'].required = True 


class CustomerWorkForm(forms.ModelForm):
    class Meta:
        model = CustomerWorkModel
        fields = [
            'work_status',
            'morning_transport_means','pickup_place',
            'pickup_staff','pickup_time',
            'pickup_car',
            'return_transport_means','dropoff_place',
            'dropoff_staff','dropoff_time',
            'dropoff_car',            
            'work1_start_time','work1_end_time','work1_place',
            'work2_start_time','work2_end_time','work2_place',
            'work3_start_time','work3_end_time','work3_place',
            'work4_start_time','work4_end_time','work4_place',
            'lunch',
            'eat_lunch_at',
            ]
        
        widgets = {
            'work_status': forms.Select,
            'morning_transport_means': forms.Select,
            'pickup_time': forms.TimeInput(attrs={'type': 'time'}),
            'return_transport_means': forms.Select,
            'dropoff_time': forms.TimeInput(attrs={'type': 'time'}),            
            'work1_start_time':forms.TimeInput(attrs={'type': 'time'}),
            'work1_end_time':forms.TimeInput(attrs={'type': 'time'}),    
            'work1_place': forms.Select,  
            'work2_start_time':forms.TimeInput(attrs={'type': 'time'}),
            'work2_end_time':forms.TimeInput(attrs={'type': 'time'}),    
            'work2_place': forms.Select,          
            'work3_start_time':forms.TimeInput(attrs={'type': 'time'}),
            'work3_end_time':forms.TimeInput(attrs={'type': 'time'}),    
            'work3_place': forms.Select,   
            'work4_start_time':forms.TimeInput(attrs={'type': 'time'}),
            'work4_end_time':forms.TimeInput(attrs={'type': 'time'}),    
            'work4_place': forms.Select,
            'lunch': forms.Select,
            'eat_lunch_at': forms.RadioSelect                
        }


    
    pickup_staff = forms.ModelChoiceField(
        queryset=StaffModel.objects.all().order_by('order'),
        required=False,
    )

    dropoff_staff = forms.ModelChoiceField(
        queryset=StaffModel.objects.all().order_by('order'),
        required=False,
    )

    def clean(self):
        cleaned_data = super().clean()
        work_status = cleaned_data.get('work_status')
        work1_place = cleaned_data.get('work1_place')
        lunch = cleaned_data.get('lunch')
        eat_lunch_at = cleaned_data.get('eat_lunch_at')

        if work_status == CustomerWorkStatusEnum.OFFICE.value:
            if not work1_place:
                self.add_error('work1_place', '勤務場所の入力は必須です。')

            if lunch == LunchEnum.ORDERED_LUNCH_BOX.value or lunch == LunchEnum.BYO_LUNCH_BOX.value:
                if not eat_lunch_at:
                    self.add_error('eat_lunch_at', '食事場所の入力は必須です。')

        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['work_status'].choices = [
            choice for choice in self.fields['work_status'].choices if choice[0] != ''
        ]


class CalendarForm(forms.Form):
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}),label='')

    def __init__(self, *args, **kwargs):
        # 'initial_date'を受け取る
        initial_date = kwargs.pop('initial_date', None)
        super().__init__(*args, **kwargs)

        # 'initial_date'が指定されている場合はその日付を初期値に設定
        if initial_date:
            self.fields['date'].initial = initial_date
        else:
            # 初期値が指定されていない場合は今日の日付を設定
            self.fields['date'].initial = datetime.date.today()