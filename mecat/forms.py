from django import forms


class RegisterMetamanForm(forms.Form):
    username = forms.CharField(max_length=30, required=True)
    password = forms.CharField(max_length=30, required=True,
                               widget=forms.PasswordInput)
    metaman = forms.FileField(required=True)
    principal_investigator = forms.CharField(required=False)
    researchers = forms.CharField(required=False)
    # ldap login!
    experiment_owner = forms.CharField(required=False)
    institution_name = forms.CharField(max_length=400, required=True)
    program_id = forms.CharField(max_length=30, required=False)
    epn = forms.CharField(max_length=30, required=True)
    start_time = forms.DateTimeField(required=False)
    end_time = forms.DateTimeField(required=False)
    title = forms.CharField(max_length=400, required=True)
    description = forms.CharField(required=False)
    beamline = forms.CharField(max_length=10, required=True)
    instrument_url = forms.CharField(max_length=255, required=False)
    instrument_scientists = forms.CharField(required=False)
    # holding sample information
    sample = forms.FileField(required=False)
