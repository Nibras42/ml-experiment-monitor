import json

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View

from apps.alerts.models import AlertRule
from apps.experiments.services import (
    get_experiment_for_user,
    get_run_for_experiment,
    list_experiments,
    list_metrics,
    list_runs,
)
from apps.pipelines.services import get_dag, get_pipeline_for_user, list_pipelines, list_stages


class WebLoginView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard:home')
        return render(request, 'dashboard/login.html')

    def post(self, request):
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=email, password=password)
        if user:
            login(request, user)
            return redirect(request.GET.get('next', 'dashboard:home'))
        return render(request, 'dashboard/login.html', {'error': 'Invalid email or password.'})


class WebLogoutView(View):
    def post(self, request):
        logout(request)
        return redirect('dashboard:login')


class DashboardHomeView(LoginRequiredMixin, View):
    def get(self, request):
        experiments = list_experiments(request.user)
        pipelines = list_pipelines(request.user)
        active_alert_count = AlertRule.objects.filter(user=request.user, is_active=True).count()
        context = {
            'experiment_count': experiments.count(),
            'pipeline_count': pipelines.count(),
            'active_alert_count': active_alert_count,
            'recent_experiments': experiments[:5],
        }
        return render(request, 'dashboard/home.html', context)


class ExperimentListView(LoginRequiredMixin, View):
    def get(self, request):
        query = request.GET.get('q', '')
        experiments = list_experiments(request.user)
        if query:
            experiments = experiments.filter(name__icontains=query)

        if request.headers.get('HX-Request'):
            return render(request, 'dashboard/experiments/partials/rows.html', {'experiments': experiments})
        return render(request, 'dashboard/experiments/list.html', {'experiments': experiments, 'query': query})


class ExperimentDetailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        experiment = get_experiment_for_user(pk, request.user)
        runs = list_runs(experiment)
        return render(request, 'dashboard/experiments/detail.html', {
            'experiment': experiment,
            'runs': runs,
        })


class RunDetailView(LoginRequiredMixin, View):
    def get(self, request, experiment_pk, run_pk):
        experiment = get_experiment_for_user(experiment_pk, request.user)
        run = get_run_for_experiment(run_pk, experiment)
        metrics = list_metrics(run)

        metric_data = {}
        for m in metrics:
            if m.name not in metric_data:
                metric_data[m.name] = {'steps': [], 'values': []}
            metric_data[m.name]['steps'].append(m.step)
            metric_data[m.name]['values'].append(m.value)

        return render(request, 'dashboard/experiments/run_detail.html', {
            'experiment': experiment,
            'run': run,
            'metric_names': list(metric_data.keys()),
            'metric_data_json': json.dumps(metric_data),
        })


class RunCompareView(LoginRequiredMixin, View):
    def get(self, request, experiment_pk):
        experiment = get_experiment_for_user(experiment_pk, request.user)
        run_ids = request.GET.getlist('runs')

        runs_data = []
        for run_id in run_ids[:5]:
            try:
                run = get_run_for_experiment(run_id, experiment)
                metrics = list_metrics(run)
                grouped = {}
                for m in metrics:
                    if m.name not in grouped:
                        grouped[m.name] = {'steps': [], 'values': []}
                    grouped[m.name]['steps'].append(m.step)
                    grouped[m.name]['values'].append(m.value)
                runs_data.append({
                    'id': str(run.id),
                    'name': run.name or str(run.id)[:8],
                    'metrics': grouped,
                })
            except Exception:
                continue

        all_metric_names = sorted({name for r in runs_data for name in r['metrics']})

        return render(request, 'dashboard/experiments/compare.html', {
            'experiment': experiment,
            'runs_data_json': json.dumps(runs_data),
            'metric_names': all_metric_names,
        })


class PipelineListView(LoginRequiredMixin, View):
    def get(self, request):
        pipelines = list_pipelines(request.user)
        return render(request, 'dashboard/pipelines/list.html', {'pipelines': pipelines})


class PipelineDetailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        pipeline = get_pipeline_for_user(pk, request.user)
        stages = list_stages(pipeline)
        dag = get_dag(pipeline)

        mermaid_lines = ['flowchart LR']
        for node in dag['nodes']:
            safe_id = node['name'].replace(' ', '_').replace('-', '_')
            label = node['name']
            mermaid_lines.append(f'    {safe_id}["{label}"]')
        for edge in dag['edges']:
            from_id = edge['from'].replace(' ', '_').replace('-', '_')
            to_id = edge['to'].replace(' ', '_').replace('-', '_')
            mermaid_lines.append(f'    {from_id} --> {to_id}')

        return render(request, 'dashboard/pipelines/detail.html', {
            'pipeline': pipeline,
            'stages': stages,
            'mermaid_definition': '\n'.join(mermaid_lines) if dag['nodes'] else '',
        })
