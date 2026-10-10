from django import forms

from .models import Product


class InventoryAdjustmentForm(forms.Form):
    quantity_change = forms.IntegerField(
        label="Quantity change",
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
    note = forms.CharField(
        max_length=500,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )

    def clean_quantity_change(self):
        quantity_change = self.cleaned_data["quantity_change"]
        if quantity_change == 0:
            raise forms.ValidationError("Quantity change cannot be zero.")
        return quantity_change


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = (
            "sku",
            "name",
            "description",
            "category",
            "supplier",
            "warehouse",
            "current_stock",
            "minimum_stock",
            "maximum_stock",
            "safety_stock",
            "supplier_lead_time",
            "unit_price",
        )
        widgets = {
            "sku": forms.TextInput(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "supplier": forms.Select(attrs={"class": "form-select"}),
            "warehouse": forms.Select(attrs={"class": "form-select"}),
            "current_stock": forms.NumberInput(attrs={"class": "form-control"}),
            "minimum_stock": forms.NumberInput(attrs={"class": "form-control"}),
            "maximum_stock": forms.NumberInput(attrs={"class": "form-control"}),
            "safety_stock": forms.NumberInput(attrs={"class": "form-control"}),
            "supplier_lead_time": forms.NumberInput(attrs={"class": "form-control"}),
            "unit_price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        minimum_stock = cleaned_data.get("minimum_stock")
        maximum_stock = cleaned_data.get("maximum_stock")
        if minimum_stock is not None and maximum_stock is not None and maximum_stock < minimum_stock:
            self.add_error("maximum_stock", "Maximum stock cannot be less than minimum stock.")
        return cleaned_data
