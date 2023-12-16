import json
from django.shortcuts import render
from django.views.generic import TemplateView
from django.conf import settings
from django.http import Http404
from django.utils import timezone

from base import mods
from voting.models import Voting
from census.models import Census


def index(request):
    votations = Voting.objects.filter(
        start_date__isnull=False, start_date__lte=timezone.now()
    )
    voting_ids = [v.id for v in votations]
    voting_cens = Census.objects.filter(voting_id__in=voting_ids)
    if request.user.is_authenticated:
        voting_cens = voting_cens.filter(voter_id=request.user.id)
        votations = votations.filter(
            id__in=voting_cens.values_list("voting_id", flat=True)
        )
    return render(request, "booth/home.html", {"votations": votations})


# TODO: check permissions and census
class BoothView(TemplateView):
    template_name = "booth/booth.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        vid = kwargs.get("voting_id", 0)

        try:
            r = mods.get("voting", params={"id": vid})
            # Casting numbers to string to manage in javascript with BigInt
            # and avoid problems with js and big number conversion
            for k, v in r[0]["pub_key"].items():
                r[0]["pub_key"][k] = str(v)

            context["voting"] = json.dumps(r[0])
        except:
            raise Http404

        context["KEYBITS"] = settings.KEYBITS

        return context
