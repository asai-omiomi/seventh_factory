# forms.py
from django import forms
from .models import StaffModel, StaffRecordModel, CustomerModel, CustomerRecordModel, StaffPatternModel, CustomerPatternModel, TransportPatternModel,StaffSessionPatternModel, CustomerSessionPatternModel, TransportRecordModel,PlaceRemarksModel,StaffSessionRecordModel, CustomerSessionRecordModel, SysAdModel, TransportTypeEnum
import datetime
   
class StaffForm(forms.ModelForm):
    class Meta:
        model = StaffModel
        fields = ['name']

class CustomerForm(forms.ModelForm):
    class Meta:
        model = CustomerModel
        fields = ['name']

MEMBER_COMMON_FIELDS = [
    'work_status',
    'remarks',
]

class BaseMemberFormMixin():

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'work_status' in self.fields:
            self.fields['work_status'].widget.attrs.update(
                {'class': 'work-status'}
            )

        if 'remarks' in self.fields:
            self.fields['remarks'].widget.attrs.update(
                {'class': 'remarks', 'rows': 2}
            )

class StaffRecordForm(BaseMemberFormMixin, forms.ModelForm):
    class Meta:
        model = StaffRecordModel
        fields=MEMBER_COMMON_FIELDS

class CustomerRecordForm(BaseMemberFormMixin, forms.ModelForm):
    class Meta:
        model = CustomerRecordModel
        fields=MEMBER_COMMON_FIELDS

class StaffPatternForm(BaseMemberFormMixin, forms.ModelForm):
    class Meta:
        model = StaffPatternModel
        fields=MEMBER_COMMON_FIELDS

class CustomerPatternForm(BaseMemberFormMixin,forms.ModelForm):
    class Meta:
        model = CustomerPatternModel
        fields=MEMBER_COMMON_FIELDS

SESSION_COMMON_FIELDS = [
    'place',
    'start_time',
    'end_time',
]

class BaseSessionFormMixin():

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for time_field in ['start_time', 'end_time']:
            if time_field in self.fields:
                self.fields[time_field].widget = forms.TimeInput(attrs={'type': 'time'})


class StaffSessionPatternForm(BaseSessionFormMixin, forms.ModelForm):
    class Meta:
        model = StaffSessionPatternModel
        fields = SESSION_COMMON_FIELDS

class StaffSessionRecordForm(BaseSessionFormMixin, forms.ModelForm):
    class Meta:
        model = StaffSessionRecordModel
        fields = SESSION_COMMON_FIELDS

class CustomerSessionPatternForm(BaseSessionFormMixin, forms.ModelForm):
    class Meta:
        model = CustomerSessionPatternModel
        fields = SESSION_COMMON_FIELDS

class CustomerSessionRecordForm(BaseSessionFormMixin, forms.ModelForm):
    class Meta:
        model = CustomerSessionRecordModel
        fields = SESSION_COMMON_FIELDS

TRANSPORT_COMMON_FIELDS = [
    'transport_means',
    'place',
    'staff',
    'remarks',
]

class BaseTransportFormMixin:

    def __init__(self, *args, transport_type: TransportTypeEnum = None, **kwargs):
        super().__init__(*args, **kwargs)

        if 'remarks' in self.fields:
            self.fields['remarks'].widget = forms.TextInput()

        if transport_type is None:
            return

        # Enum → class 名
        type_class = {
            TransportTypeEnum.MORNING: 'morning',
            TransportTypeEnum.RETURN: 'return',
        }.get(transport_type)

        if not type_class:
            return

        # 送迎
        if 'transport_means' in self.fields:
            self.fields['transport_means'].widget.attrs.setdefault('class', '')
            self.fields['transport_means'].widget.attrs['class'] += f' {type_class}'

        # 関連フィールド
        for name in ['place', 'staff', 'remarks']:
            if name in self.fields:
                self.fields[name].widget.attrs.setdefault('class', '')
                self.fields[name].widget.attrs['class'] += f' {type_class}-fields'

class TransportPatternForm(BaseTransportFormMixin, forms.ModelForm):

    staff = forms.ModelChoiceField(
        queryset=StaffModel.objects.none(),
        required=False,
    )

    class Meta:
        model = TransportPatternModel
        fields = TRANSPORT_COMMON_FIELDS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['staff'].queryset = StaffModel.objects.all().order_by('order')

class TransportRecordForm(BaseTransportFormMixin, forms.ModelForm):

    staff = forms.ModelChoiceField(
        queryset=StaffModel.objects.none(),
        required=False,
    )

    class Meta:
        model = TransportRecordModel
        fields = TRANSPORT_COMMON_FIELDS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['staff'].queryset = StaffModel.objects.all().order_by('order')

class CalendarForm(forms.Form):
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}),label='')

    def __init__(self, *args, **kwargs):
        initial_date = kwargs.pop('initial_date', None)

        super().__init__(*args, **kwargs)

        # 'initial_date'が指定されている場合はその日付を初期値に設定
        if initial_date:
            self.fields['date'].initial = initial_date
        else:
            self.fields['date'].initial = datetime.date.today()

class PlaceRemarksForm(forms.ModelForm):
      
    remarks = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'style': 'display: inline; max-width:800px',
        }),
        required=False
    )
    
    class Meta:
        model = PlaceRemarksModel
        fields = ['remarks']

class OutputForm(forms.Form):
    TARGET_CHOICES = [
        ('customer', '利用者'),
        ('staff', 'スタッフ'),
    ]

    target = forms.ChoiceField(
        choices=TARGET_CHOICES,
        widget=forms.RadioSelect(),
        label='対象',
        initial='customer'
    )

class SysAdForm(forms.ModelForm):
    class Meta:
        model = SysAdModel
        fields = ["auto_mode_days"]

    auto_mode_days = forms.IntegerField(
        min_value=0,
        max_value=10,
        label="自動作成日数",
    )