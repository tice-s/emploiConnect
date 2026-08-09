// EmploiConnect — petites améliorations UX côté client (progressive enhancement).
document.addEventListener("DOMContentLoaded", () => {
    // Fermeture automatique des alertes après quelques secondes.
    document.querySelectorAll(".alert").forEach((alert) => {
        setTimeout(() => {
            const closeBtn = alert.querySelector(".btn-close");
            if (closeBtn) closeBtn.click();
        }, 6000);
    });

    // Désactive un bouton de soumission après clic pour éviter les doubles envois
    // (utile notamment pour les actions IA, plus longues qu'une requête classique).
    document.querySelectorAll("form[data-ai-action]").forEach((form) => {
        form.addEventListener("submit", () => {
            const btn = form.querySelector("button[type=submit]");
            if (btn) {
                btn.disabled = true;
                btn.dataset.originalText = btn.innerHTML;
                btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Analyse IA en cours...';
            }
        });
    });

    // Animation légère d'apparition au défilement pour les cartes (offres,
    // suggestions...). Respecte prefers-reduced-motion via le CSS associé.
    const revealTargets = document.querySelectorAll(".card.card-hover");
    if ("IntersectionObserver" in window && revealTargets.length) {
        revealTargets.forEach((el) => el.classList.add("reveal-on-scroll"));
        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    entry.target.classList.add("is-visible");
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.1 });
        revealTargets.forEach((el) => observer.observe(el));
    }

    // Indicateur visuel de sélection pour les sélecteurs de style/couleur de CV
    // (repose sur CSS :has() dans les navigateurs récents, secours JS ici pour
    // une compatibilité plus large).
    document.querySelectorAll(".style-picker, .style-gallery, .theme-picker").forEach((group) => {
        const sync = () => {
            group.querySelectorAll("label").forEach((label) => {
                const input = label.querySelector("input[type=radio]");
                label.classList.toggle("is-selected", !!input && input.checked);
            });
        };
        group.addEventListener("change", sync);
        sync();
    });
});
