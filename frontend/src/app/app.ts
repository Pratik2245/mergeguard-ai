import { Component, OnInit, signal, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RiskService } from './services/risk.service';
import { AuthService } from './services/auth.service';
import {
  RiskPrediction,
  PredictionSummary,
  Analytics,
  DirectPredictRequest,
  GitDiffPredictRequest,
  GitLabMRRequest,
  MongoStatus,
} from './models/risk.model';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App implements OnInit {
  private riskService = inject(RiskService);
  public authService = inject(AuthService);

  // Active navigation view
  activeTab = signal<'dashboard' | 'direct' | 'diff' | 'gitlab' | 'history' | 'model'>('dashboard');

  // Application State Signals
  backendHealthy = signal<boolean>(false);
  modelInfo = signal<any>(null);
  mongoStatus = signal<MongoStatus | null>(null);
  analytics = signal<Analytics | null>(null);
  history = signal<PredictionSummary[]>([]);
  activePrediction = signal<RiskPrediction | null>(null);
  isLoading = signal<boolean>(false);
  errorMessage = signal<string | null>(null);
  toastMessage = signal<string | null>(null);
  selectedHistoryFilter = signal<string>('ALL');
  searchQuery = signal<string>('');

  // Authentication Modal State
  showAuthModal = signal<boolean>(false);
  authMode = signal<'login' | 'register'>('login');
  authError = signal<string | null>(null);

  loginForm = {
    username_or_email: 'admin@mergeguard.ai',
    password: 'adminpassword123',
  };

  registerForm = {
    email: '',
    username: '',
    password: '',
    full_name: '',
  };

  // Circumference for SVG gauge (r = 46)
  readonly GAUGE_CIRCUMFERENCE = 2 * Math.PI * 46; // ~289.02

  // Direct Form Model
  directForm: DirectPredictRequest = {
    project_name: 'gitlab-org/gitlab',
    mr_iid: 1542,
    mr_title: 'Refactor authentication permission gate & session store',
    la: 420,
    ld: 110,
    nf: 14,
    nd: 5,
    ns: 2,
    ent: 2.8,
    ndev: 4,
    age: 65,
    nuc: 22,
    aexp: 80,
    arexp: 60,
    asexp: 8,
    tests_modified: false,
    critical_modules: true,
  };

  // Git Diff Form Model
  diffForm: GitDiffPredictRequest = {
    project_name: 'mergeguard/auth-microservice',
    mr_iid: 88,
    mr_title: 'Enforce constant-time hash comparison and session invalidation',
    diff_text: `diff --git a/services/security.py b/services/security.py
--- a/services/security.py
+++ b/services/security.py
@@ -10,3 +10,14 @@ def verify_auth_token(token):
+    if not token or len(token) < 32:
+        raise ValueError("Invalid authentication token format")
+    # Enforce constant-time token comparison to prevent timing attacks
+    is_valid = secrets.compare_digest(stored_hash, user_token)
+    if not is_valid:
+        logger.warning("Authentication failed: invalid token provided")
+        return False
+    return True
diff --git a/tests/test_security.py b/tests/test_security.py
--- a/tests/test_security.py
+++ b/tests/test_security.py
@@ -25,0 +26,8 @@
+def test_verify_auth_token_timing_safe():
+    with pytest.raises(ValueError):
+        verify_auth_token("short_token")
+    assert verify_auth_token(VALID_SECRET_TOKEN) is True
`,
    aexp: 180,
    arexp: 140,
    asexp: 45,
  };

  // GitLab MR Form Model
  gitlabForm: GitLabMRRequest = {
    gitlab_url: 'https://gitlab.com',
    project_id: 'gitlab-org/gitlab',
    mr_iid: 14209,
    private_token: '',
  };

  // Filtered audit list with search & risk tier
  filteredHistory = computed(() => {
    let items = this.history();
    const filter = this.selectedHistoryFilter();
    const query = this.searchQuery().trim().toLowerCase();

    if (filter !== 'ALL') {
      items = items.filter((item) => item.risk_level === filter);
    }

    if (query) {
      items = items.filter(
        (item) =>
          item.project_name.toLowerCase().includes(query) ||
          (item.mr_title && item.mr_title.toLowerCase().includes(query)) ||
          (item.mr_iid && item.mr_iid.toString().includes(query))
      );
    }

    return items;
  });

  ngOnInit() {
    this.checkHealth();
    this.loadAnalytics();
    this.loadHistory();
    this.loadModelInfo();
    this.loadMongoStatus();
  }

  checkHealth() {
    this.riskService.getHealth().subscribe({
      next: (res) => {
        this.backendHealthy.set(res.status === 'healthy');
      },
      error: () => this.backendHealthy.set(false),
    });
  }

  loadMongoStatus() {
    this.riskService.getMongoStatus().subscribe({
      next: (status) => this.mongoStatus.set(status),
      error: (err) => console.error('MongoDB status error', err),
    });
  }

  loadModelInfo() {
    this.riskService.getModelInfo().subscribe({
      next: (info) => this.modelInfo.set(info),
      error: (err) => console.error('Could not load model info', err),
    });
  }

  loadAnalytics() {
    this.riskService.getAnalytics().subscribe({
      next: (data) => this.analytics.set(data),
      error: (err) => console.error('Analytics load error', err),
    });
  }

  loadHistory(filter: string = 'ALL') {
    this.selectedHistoryFilter.set(filter);
    this.riskService.getPredictions(filter).subscribe({
      next: (items) => this.history.set(items),
      error: (err) => console.error('History load error', err),
    });
  }

  setTab(tab: 'dashboard' | 'direct' | 'diff' | 'gitlab' | 'history' | 'model') {
    this.activeTab.set(tab);
    this.errorMessage.set(null);
    if (tab === 'history') {
      this.loadHistory(this.selectedHistoryFilter());
    } else if (tab === 'dashboard') {
      this.loadAnalytics();
    }
  }

  showToast(message: string) {
    this.toastMessage.set(message);
    setTimeout(() => {
      this.toastMessage.set(null);
    }, 3800);
  }

  // Auth Modal Handlers
  openAuth(mode: 'login' | 'register' = 'login') {
    this.authMode.set(mode);
    this.authError.set(null);
    this.showAuthModal.set(true);
  }

  closeAuth() {
    this.showAuthModal.set(false);
    this.authError.set(null);
  }

  submitLogin() {
    this.authError.set(null);
    this.isLoading.set(true);
    this.authService.login(this.loginForm).subscribe({
      next: (res) => {
        this.isLoading.set(false);
        this.closeAuth();
        this.showToast(`Welcome back, ${res.user.full_name || res.user.username}! ✨`);
      },
      error: (err) => {
        this.isLoading.set(false);
        this.authError.set(err?.error?.detail || 'Invalid username/email or password');
      },
    });
  }

  submitRegister() {
    this.authError.set(null);
    this.isLoading.set(true);
    this.authService.register(this.registerForm).subscribe({
      next: (res) => {
        this.isLoading.set(false);
        this.closeAuth();
        this.showToast(`Account created for ${res.user.username}! ✨`);
      },
      error: (err) => {
        this.isLoading.set(false);
        this.authError.set(err?.error?.detail || 'Failed to register account');
      },
    });
  }

  logout() {
    this.authService.logout();
    this.showToast('You have been signed out.');
  }

  submitDirect() {
    this.isLoading.set(true);
    this.errorMessage.set(null);
    this.riskService.predictDirect(this.directForm).subscribe({
      next: (result) => {
        this.activePrediction.set(result);
        this.isLoading.set(false);
        this.showToast(`Analyzed MR: Score ${result.risk_score}/100 [${result.risk_level}]`);
        this.loadAnalytics();
        this.loadHistory();
      },
      error: (err) => {
        this.isLoading.set(false);
        this.errorMessage.set(err?.error?.detail || 'Failed to analyze metrics');
      },
    });
  }

  submitDiff() {
    if (!this.diffForm.diff_text.trim()) {
      this.errorMessage.set('Please provide a unified git diff');
      return;
    }
    this.isLoading.set(true);
    this.errorMessage.set(null);
    this.riskService.predictDiff(this.diffForm).subscribe({
      next: (result) => {
        this.activePrediction.set(result);
        this.isLoading.set(false);
        this.showToast(`Diff parsed successfully: ${result.risk_score}/100 [${result.risk_level}]`);
        this.loadAnalytics();
        this.loadHistory();
      },
      error: (err) => {
        this.isLoading.set(false);
        this.errorMessage.set(err?.error?.detail || 'Failed to parse and analyze git diff');
      },
    });
  }

  submitGitLab() {
    if (!this.gitlabForm.project_id || !this.gitlabForm.mr_iid) {
      this.errorMessage.set('Please provide Project ID and MR IID');
      return;
    }
    this.isLoading.set(true);
    this.errorMessage.set(null);
    this.riskService.predictGitLab(this.gitlabForm).subscribe({
      next: (result) => {
        this.activePrediction.set(result);
        this.isLoading.set(false);
        this.showToast(`Fetched GitLab MR !${result.mr_iid}: ${result.risk_score}/100 [${result.risk_level}]`);
        this.loadAnalytics();
        this.loadHistory();
      },
      error: (err) => {
        this.isLoading.set(false);
        this.errorMessage.set(err?.error?.detail || 'Could not fetch GitLab MR. Please verify Project ID / MR number.');
      },
    });
  }

  viewPredictionDetail(id: number) {
    this.isLoading.set(true);
    this.riskService.getPredictionDetail(id).subscribe({
      next: (detail) => {
        this.activePrediction.set(detail);
        this.isLoading.set(false);
        this.setTab('direct');
      },
      error: (err) => {
        this.isLoading.set(false);
        this.errorMessage.set('Could not load prediction details');
      },
    });
  }

  loadPreset(presetName: string) {
    if (presetName === 'high-risk') {
      this.directForm = {
        project_name: 'gitlab-org/gitlab',
        mr_iid: 19401,
        mr_title: 'Massive database schema migration and auth overhaul',
        la: 1250,
        ld: 480,
        nf: 32,
        nd: 11,
        ns: 4,
        ent: 3.85,
        ndev: 9,
        age: 210,
        nuc: 45,
        aexp: 20,
        arexp: 15,
        asexp: 2,
        tests_modified: false,
        critical_modules: true,
      };
      this.showToast('Loaded scenario: "Critical Auth Refactor"');
    } else if (presetName === 'low-risk') {
      this.directForm = {
        project_name: 'apache/groovy',
        mr_iid: 2011,
        mr_title: 'Add unit tests for string utility helper',
        la: 35,
        ld: 5,
        nf: 2,
        nd: 1,
        ns: 1,
        ent: 0.35,
        ndev: 1,
        age: 20,
        nuc: 8,
        aexp: 420,
        arexp: 350,
        asexp: 200,
        tests_modified: true,
        critical_modules: false,
      };
      this.showToast('Loaded scenario: "Atomic Unit Test Fix"');
    } else if (presetName === 'medium-risk') {
      this.directForm = {
        project_name: 'kubernetes/kubernetes',
        mr_iid: 8943,
        mr_title: 'Update controller reconciliation loop timeout',
        la: 140,
        ld: 60,
        nf: 6,
        nd: 3,
        ns: 2,
        ent: 1.8,
        ndev: 4,
        age: 90,
        nuc: 18,
        aexp: 180,
        arexp: 140,
        asexp: 30,
        tests_modified: true,
        critical_modules: true,
      };
      this.showToast('Loaded scenario: "Controller Loop Timeout"');
    }
  }

  copyMarkdownReport() {
    const p = this.activePrediction();
    if (!p) return;

    const report = `### MergeGuard AI — Risk Analysis Report
* **Risk Score**: ${p.risk_score}/100 (${p.risk_level})
* **Defect Probability**: ${(p.defect_probability * 100).toFixed(1)}%
* **Project**: ${p.project_name} ${p.mr_iid ? `!${p.mr_iid}` : ''}
* **Churn**: +${p.metrics_summary.lines_added} / -${p.metrics_summary.lines_deleted} across ${p.metrics_summary.files_changed} files
* **Entropy**: ${p.metrics_summary.entropy}
* **Audited by**: ${p.created_by_user || 'Anonymous'}

#### Contributing Risk Factors:
${p.top_risk_factors.map((f) => `- **${f.label}**: ${f.value} (${f.description})`).join('\n') || '- None'}

#### Recommendations:
${p.recommendations.map((r) => `- [ ] ${r}`).join('\n')}`;

    navigator.clipboard.writeText(report).then(() => {
      this.showToast('Copied Markdown review report to clipboard! 📋');
    });
  }

  // SVG Gauge Dashoffset calculation
  getGaugeDashOffset(score: number): number {
    const clamped = Math.min(Math.max(score, 0), 100);
    return this.GAUGE_CIRCUMFERENCE - (this.GAUGE_CIRCUMFERENCE * clamped) / 100;
  }

  getScoreColorClass(score: number): string {
    if (score >= 70) return 'score-high';
    if (score >= 40) return 'score-medium';
    return 'score-low';
  }

  getRiskBadgeClass(level: string): string {
    switch (level) {
      case 'HIGH':
        return 'badge-high';
      case 'MEDIUM':
        return 'badge-medium';
      default:
        return 'badge-low';
    }
  }
}
