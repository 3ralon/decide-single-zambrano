import json
from django.shortcuts import redirect, render
from django.views.generic import TemplateView
from django.conf import settings
from django.http import Http404, HttpResponseNotFound, HttpResponse
from django.core.exceptions import PermissionDenied
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


class BoothView(TemplateView):
    template_name = "booth/booth.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            if self.request.user.is_anonymous:
                raise PermissionDenied()
            # Check if voting exists and is active
            vid = kwargs.get("voting_id", 0)
            voting_exists = Voting.objects.filter(
                id=vid, start_date__isnull=False, start_date__lte=timezone.now()
            ).exists()
            if not voting_exists:
                raise Http404()
            # Check if user is in census
            user_census_exists = Census.objects.filter(
                voter_id=self.request.user.id, voting_id=vid
            ).exists()
            if not user_census_exists:
                raise PermissionDenied()
            r = mods.get("voting", params={"id": vid})
            # Casting numbers to string to manage in javascript with BigInt
            # and avoid problems with js and big number conversions
            for k, v in r[0]["pub_key"].items():
                r[0]["pub_key"][k] = str(v)
            context["voting"] = json.dumps(r[0])
        except Exception as e:
            context["failed"] = True
            context["http_error"] = e
            return context
        context["KEYBITS"] = settings.KEYBITS
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        if 'failed' in context:
            if isinstance(context['http_error'], Http404):
                return HttpResponseNotFound()
            elif isinstance(context['http_error'], PermissionDenied) and request.user.is_anonymous:
                return redirect(settings.LOGIN_URL)
            else:
                return HttpResponse("No estás autorizado para votar en esta votación.", status=401)
        return render(request, self.template_name, context)