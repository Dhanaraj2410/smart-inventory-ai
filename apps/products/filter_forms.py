from django import forms
from django.contrib.auth import get_user_model


class InventoryAdjustmentFilterForm(forms.Form):
    DIRECTION_CHOICES = (
        ("", "All changes"),
        ("increase", "Stock increases"),
        ("decrease", "Stock decreases"),
    )

    q = forms.CharField(required=False, max_length=200)
    start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    direction = forms.ChoiceField(required=False, choices=DIRECTION_CHOICES)
    created_by = forms.ModelChoiceField(
        required=False,
        queryset=get_user_model().objects.none(),
        empty_label="All users",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["created_by"].queryset = get_user_model().objects.filter(
            inventory_adjustments__isnull=False
        ).distinct().order_by("username")

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        if start_date and end_date and start_date > end_date:
            self.add_error("end_date", "End date must be on or after the start date.")
        return cleaned_data
