from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from ai_engine.services import (
    AIServiceError, evaluate_interview_answer, generate_interview_questions, summarize_interview_session,
)
from candidates.models import CandidateProfile
from jobs.models import JobOffer
from .forms import AnswerForm, StartInterviewForm
from .models import InterviewAnswer, InterviewQuestion, InterviewSession


def _profile_summary_text(profile: CandidateProfile) -> str:
    from applications.views import _build_candidate_summary
    return _build_candidate_summary(profile)


@login_required
def start_session(request):
    """
    Le candidat clique "Préparer mon entretien" : l'IA analyse son profil et le
    poste visé, puis génère une série de questions réalistes (V1 texte).
    """
    if not (request.user.is_candidate and hasattr(request.user, "candidate_profile")):
        messages.error(request, "Cette fonctionnalité est réservée aux candidats.")
        return redirect("dashboard:redirect")

    profile = request.user.candidate_profile
    job = None
    job_id = request.GET.get("job")
    initial = {}
    if job_id:
        job = JobOffer.objects.filter(pk=job_id).first()
        if job:
            initial = {"job_id": job.pk, "company_name": job.company.name, "position_title": job.title}

    if request.method == "POST":
        form = StartInterviewForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            description = data.get("job_description") or (job.description if job else "")
            try:
                questions = generate_interview_questions(
                    job_title=data["position_title"],
                    company_name=data.get("company_name") or (job.company.name if job else "l'entreprise"),
                    job_description=description,
                    candidate_summary=_profile_summary_text(profile),
                    user=request.user,
                )
            except AIServiceError as exc:
                messages.error(request, str(exc))
                return render(request, "interview_prep/start.html", {"form": form})

            session = InterviewSession.objects.create(
                candidate=profile,
                job=job,
                company_name=data.get("company_name") or (job.company.name if job else ""),
                position_title=data["position_title"],
            )
            for i, q in enumerate(questions):
                InterviewQuestion.objects.create(
                    session=session, order=i, question_text=q["question"], category=q.get("category", "")
                )
            return redirect("interview_prep:session_detail", pk=session.pk)
    else:
        form = StartInterviewForm(initial=initial)
    return render(request, "interview_prep/start.html", {"form": form})


@login_required
def session_detail(request, pk):
    session = get_object_or_404(InterviewSession, pk=pk, candidate__user=request.user)
    questions = session.questions.select_related("answer").all()
    return render(request, "interview_prep/session_detail.html", {
        "session": session, "questions": questions, "form": AnswerForm(),
    })


@login_required
def submit_answer(request, pk):
    question = get_object_or_404(InterviewQuestion, pk=pk, session__candidate__user=request.user)
    if hasattr(question, "answer"):
        messages.info(request, "Vous avez déjà répondu à cette question.")
        return redirect("interview_prep:session_detail", pk=question.session_id)

    if request.method == "POST":
        form = AnswerForm(request.POST)
        if form.is_valid():
            try:
                feedback = evaluate_interview_answer(
                    question=question.question_text,
                    answer=form.cleaned_data["answer_text"],
                    job_title=question.session.position_title,
                    user=request.user,
                )
            except AIServiceError as exc:
                messages.error(request, str(exc))
                return redirect("interview_prep:session_detail", pk=question.session_id)

            InterviewAnswer.objects.create(
                question=question,
                answer_text=form.cleaned_data["answer_text"],
                ai_feedback=feedback.get("feedback", ""),
                relevance_score=feedback.get("relevance_score"),
                structure_score=feedback.get("structure_score"),
            )
    return redirect("interview_prep:session_detail", pk=question.session_id)


@login_required
def complete_session(request, pk):
    session = get_object_or_404(InterviewSession, pk=pk, candidate__user=request.user)
    questions = list(session.questions.select_related("answer").all())
    if any(not hasattr(q, "answer") for q in questions):
        messages.warning(request, "Répondez à toutes les questions avant de terminer la session.")
        return redirect("interview_prep:session_detail", pk=pk)

    try:
        summary = summarize_interview_session(
            qa_pairs=[
                {"question": q.question_text, "category": q.category, "answer": q.answer.answer_text}
                for q in questions
            ],
            user=request.user,
        )
    except AIServiceError as exc:
        messages.error(request, str(exc))
        return redirect("interview_prep:session_detail", pk=pk)

    session.overall_feedback = summary.get("overall_feedback", "")
    session.confidence_score = summary.get("confidence_score")
    session.communication_score = summary.get("communication_score")
    session.technical_score = summary.get("technical_score")
    session.completed_at = timezone.now()
    session.save()
    messages.success(request, "Session d'entretien terminée ! Consultez votre bilan ci-dessous.")
    return redirect("interview_prep:session_detail", pk=pk)


@login_required
def session_list(request):
    profile = getattr(request.user, "candidate_profile", None)
    sessions = InterviewSession.objects.filter(candidate=profile) if profile else InterviewSession.objects.none()
    return render(request, "interview_prep/session_list.html", {"sessions": sessions})
