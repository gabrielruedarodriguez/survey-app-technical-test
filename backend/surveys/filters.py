from django import forms
from django.utils.translation import gettext_lazy as _
from django_filters import DateFilter, FilterSet


class ResponseFilterForm(forms.Form):
    def clean(self):
        cleaned_data = super().clean()
        date_from, date_to = cleaned_data.get("from"), cleaned_data.get("to")
        if date_from and date_to and date_from > date_to:
            self.add_error("to", _("Must be on or after 'from'."))
        return cleaned_data


class ResponseFilter(FilterSet):
    class Meta:
        form = ResponseFilterForm

    @classmethod
    def get_filters(cls):
        # "from" is a Python keyword, so these filters cannot be class attributes.
        filters = super().get_filters()
        filters["from"] = DateFilter(field_name="submitted_at", lookup_expr="date__gte")
        filters["to"] = DateFilter(field_name="submitted_at", lookup_expr="date__lte")
        return filters
