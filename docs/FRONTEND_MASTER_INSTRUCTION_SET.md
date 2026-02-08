# HR Automation Platform — Frontend Master Instruction Set

> **Version:** 1.0 | **Stack:** SvelteKit 2.x + Svelte 5 Runes | **Design:** Executive Dark Theme

---

## 0. APPLICATION FLOW OVERVIEW

This platform follows a strict hierarchical flow. Each step must be completed before the next:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        HR AUTOMATION PLATFORM FLOW                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  STEP 1: COMPANY REGISTRATION                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  POST /company/register                                              │   │
│  │  → Company Name, Email, Password, Industry, Size                     │   │
│  │  → Returns: company_id, workspace_id, user_id                        │   │
│  │  → Store workspace_id & user_id in localStorage for all API calls    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              ↓                                              │
│  STEP 2: CREATE JOB REQUIREMENTS                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  POST /job-requirements/company/{company_id}                         │   │
│  │  → Title, Department, Description, Skills, Experience, Salary        │   │
│  │  → Returns: job_requirement_id                                       │   │
│  │  → Job appears on Dashboard with status "draft" or "active"          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              ↓                                              │
│  STEP 3: DASHBOARD POPULATES                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Dashboard shows:                                                    │   │
│  │  • Company profile & stats                                           │   │
│  │  • List of Job Requirements (with candidate counts)                  │   │
│  │  • Candidates per job (pipeline stages)                              │   │
│  │  • Interview statistics & analytics                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              ↓                                              │
│  STEP 4: CANDIDATES APPLY (External)                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  GET /candidates/{job_id}/apply-form → Dynamic application form      │   │
│  │  POST /candidates/apply → Submit application with resume             │   │
│  │  → Candidates appear in Dashboard under the job                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              ↓                                              │
│  STEP 5: AI RESUME SCREENING                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  POST /candidates/{job_id}/select-top-resumes                        │   │
│  │  → AI ranks candidates, generates passwords                          │   │
│  │  → Selected candidates move to "aptitude_eligible" stage             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              ↓                                              │
│  STEP 6: APTITUDE TEST                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  POST /aptitude/create → Configure test for job                      │   │
│  │  Candidate: Login → Take Test → Submit                               │   │
│  │  POST /aptitude/select-top-candidates → Rank by scores               │   │
│  │  → Passed candidates move to "technical_eligible" stage              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              ↓                                              │
│  STEP 7: TECHNICAL INTERVIEW (AI)                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  POST /technical-interview/start/{candidate_id}                      │   │
│  │  → WebSocket connection for real-time AI interview                   │   │
│  │  POST /technical-interview/complete/{id} → Store results             │   │
│  │  POST /technical-interview/select-top-candidates → Rank              │   │
│  │  → Passed candidates move to "hr_eligible" stage                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              ↓                                              │
│  STEP 8: HR INTERVIEW (AI)                                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  POST /hr-interview/start/{candidate_id}                             │   │
│  │  → WebSocket connection for real-time AI HR interview                │   │
│  │  POST /hr-interview/complete/{id} → Store results                    │   │
│  │  POST /hr-interview/select-top-candidates → Final ranking            │   │
│  │  → Top candidates marked as "hire_recommended"                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**CRITICAL:** All API calls require `workspace-id` and `user-id` headers (obtained from company registration).

---

## 1. PROJECT INITIALIZATION

```bash
pnpm create svelte@latest hr-automation-frontend
# Select: Skeleton project, TypeScript, ESLint, Prettier, Playwright

cd hr-automation-frontend
pnpm add -D tailwindcss postcss autoprefixer
pnpm add @tanstack/svelte-query openapi-fetch svelte-sonner lucide-svelte clsx tailwind-merge
pnpm add -D openapi-typescript
npx tailwindcss init -p
npx shadcn-svelte@latest init
```

---

## 2. FOLDER ARCHITECTURE

```
src/
├── lib/
│   ├── api/
│   │   ├── client.ts                 # openapi-fetch configured client
│   │   ├── generated.ts              # Auto-generated types from YAML
│   │   ├── queries/
│   │   │   ├── candidates.ts         # TanStack Query hooks
│   │   │   ├── jobs.ts
│   │   │   ├── interviews.ts
│   │   │   ├── companies.ts
│   │   │   └── aptitude.ts
│   │   └── mutations/
│   │       ├── companies.ts          # Register, update company
│   │       ├── jobs.ts               # Create, update job requirements
│   │       ├── candidates.ts         # Select top resumes
│   │       ├── aptitude.ts           # Create test, select top
│   │       └── interviews.ts         # Start, complete interviews
│   │
│   ├── components/
│   │   ├── ui/                       # shadcn-svelte primitives
│   │   ├── layout/
│   │   │   ├── Sidebar.svelte
│   │   │   ├── Header.svelte
│   │   │   └── PageShell.svelte
│   │   ├── auth/
│   │   │   ├── RegisterForm.svelte   # Company registration
│   │   │   └── LoginForm.svelte
│   │   ├── company/
│   │   │   ├── CompanyProfile.svelte
│   │   │   └── CompanySettings.svelte
│   │   ├── jobs/
│   │   │   ├── JobForm.svelte        # Create/edit job requirement
│   │   │   ├── JobCard.svelte
│   │   │   ├── JobList.svelte
│   │   │   └── SkillsInput.svelte    # Multi-skill selector
│   │   ├── candidates/
│   │   │   ├── CandidateTable.svelte
│   │   │   ├── CandidateCard.svelte
│   │   │   ├── PipelineView.svelte   # Kanban-style stages
│   │   │   └── ResumeViewer.svelte
│   │   ├── interview/
│   │   │   ├── VideoPreview.svelte   # Candidate webcam
│   │   │   ├── AudioVisualizer.svelte
│   │   │   ├── TranscriptPanel.svelte
│   │   │   ├── ControlBar.svelte
│   │   │   └── InterviewTimer.svelte
│   │   ├── dashboard/
│   │   │   ├── StatCard.svelte
│   │   │   ├── JobsOverview.svelte
│   │   │   ├── RecentCandidates.svelte
│   │   │   └── InterviewHistory.svelte
│   │   └── shared/
│   │       ├── StatusBadge.svelte
│   │       ├── ScoreGauge.svelte
│   │       └── ConfirmDialog.svelte
│   │
│   ├── stores/
│   │   ├── auth.svelte.ts            # Company auth state
│   │   ├── media.svelte.ts           # Camera/mic state (Svelte 5)
│   │   ├── interview.svelte.ts       # WebSocket + transcript
│   │   └── ui.svelte.ts              # Sidebar, theme
│   │
│   ├── utils/
│   │   ├── cn.ts                     # clsx + tailwind-merge
│   │   ├── format.ts                 # Date, score formatters
│   │   └── permissions.ts            # Media permission helpers
│   │
│   └── constants/
│       ├── theme.ts                  # Color tokens
│       └── routes.ts
│
├── routes/
│   ├── +layout.svelte
│   ├── +page.svelte                  # Landing → redirect based on auth
│   │
│   ├── (auth)/
│   │   ├── +layout.svelte            # Auth layout (no sidebar)
│   │   ├── register/+page.svelte     # Company registration
│   │   └── login/+page.svelte        # Company login
│   │
│   ├── (dashboard)/
│   │   ├── +layout.svelte            # Dashboard shell with sidebar
│   │   ├── +page.svelte              # Overview (jobs, stats, recent)
│   │   │
│   │   ├── company/
│   │   │   └── +page.svelte          # Company profile & settings
│   │   │
│   │   ├── jobs/
│   │   │   ├── +page.svelte          # All job requirements list
│   │   │   ├── new/+page.svelte      # Create new job requirement
│   │   │   └── [job_id]/
│   │   │       ├── +page.svelte      # Job detail + candidates pipeline
│   │   │       ├── edit/+page.svelte # Edit job requirement
│   │   │       ├── aptitude/+page.svelte    # Aptitude test config
│   │   │       ├── technical/+page.svelte   # Technical interviews list
│   │   │       └── hr/+page.svelte          # HR interviews list
│   │   │
│   │   ├── candidates/
│   │   │   ├── +page.svelte          # All candidates across jobs
│   │   │   └── [candidate_id]/
│   │   │       └── +page.svelte      # Candidate profile + interview history
│   │   │
│   │   └── analytics/
│   │       └── +page.svelte          # Hiring velocity, funnel, scores
│   │
│   ├── interview/
│   │   ├── technical/[session]/+page.svelte  # Technical interview UI
│   │   └── hr/[session]/+page.svelte         # HR interview UI
│   │
│   └── apply/
│       └── [job_id]/+page.svelte     # Public candidate application form
│
└── app.css
```

---

## 3. VISUAL IDENTITY — "EXECUTIVE DARK" THEME

### 3.1 Color System (tailwind.config.ts)

```typescript
export default {
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // PRIMARY — Obsidian (Authority)
        obsidian: {
          950: '#09090B',  // Deepest background
          900: '#0C0C0F',  // Card backgrounds
          850: '#111114',  // Elevated surfaces
          800: '#18181B',  // Borders, dividers
        },
        // NEUTRAL — Deep Slate
        slate: {
          900: '#0F172A',
          800: '#1E293B',
          700: '#334155',
          600: '#475569',
          500: '#64748B',
          400: '#94A3B8',
          300: '#CBD5E1',
          200: '#E2E8F0',
          100: '#F1F5F9',
        },
        // ACCENT — Metallic Silver
        silver: {
          DEFAULT: '#A8A8A8',
          light: '#D4D4D8',
          muted: '#71717A',
        },
        // SEMANTIC (muted, professional)
        success: '#10B981',
        warning: '#F59E0B',
        error: '#EF4444',
        info: '#3B82F6',
      },
      fontFamily: {
        sans: ['Inter', 'Geist Sans', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      backdropBlur: {
        glass: '12px',
      },
    },
  },
};
```

### 3.2 Global Styles (app.css)

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --radius: 0.5rem;
  }
  
  body {
    @apply bg-obsidian-950 text-slate-200 antialiased;
    font-feature-settings: 'cv02', 'cv03', 'cv04', 'cv11';
  }
  
  /* Executive scrollbar */
  ::-webkit-scrollbar {
    width: 6px;
    height: 6px;
  }
  ::-webkit-scrollbar-track {
    @apply bg-obsidian-900;
  }
  ::-webkit-scrollbar-thumb {
    @apply bg-slate-700 rounded-full hover:bg-slate-600;
  }
}

@layer components {
  /* Glassmorphic surface */
  .glass {
    @apply bg-obsidian-900/80 backdrop-blur-glass border border-slate-800/50;
  }
  
  /* Executive card */
  .card-executive {
    @apply bg-obsidian-900 border border-slate-800/50 rounded-lg shadow-xl shadow-black/20;
  }
}
```

---

## 4. TYPE-SAFE API LAYER

### 4.1 Generate Types

```bash
# Add to package.json scripts
"generate:types": "openapi-typescript ./swagger/new-swagger.yaml -o ./src/lib/api/generated.ts"
```

### 4.2 API Client (src/lib/api/client.ts)

```typescript
import createClient from 'openapi-fetch';
import type { paths } from './generated';

const MAIN_API = 'http://localhost:8888/interview-management-service/api/v1';
const TECH_INTERVIEW_API = 'http://localhost:8100';
const HR_INTERVIEW_API = 'http://localhost:8200';

function createApiClient(baseUrl: string) {
  const client = createClient<paths>({ baseUrl });
  
  client.use({
    onRequest({ request }) {
      const workspaceId = localStorage.getItem('workspace-id');
      const userId = localStorage.getItem('user-id');
      if (workspaceId) request.headers.set('workspace-id', workspaceId);
      if (userId) request.headers.set('user-id', userId);
      return request;
    },
    onResponse({ response }) {
      if (response.status === 401) window.location.href = '/login';
      return response;
    },
  });
  
  return client;
}

export const api = createApiClient(MAIN_API);
export const techInterviewApi = createApiClient(TECH_INTERVIEW_API);
export const hrInterviewApi = createApiClient(HR_INTERVIEW_API);
```

### 4.3 TanStack Query Setup (src/routes/+layout.svelte)

```svelte
<script lang="ts">
  import { QueryClient, QueryClientProvider } from '@tanstack/svelte-query';
  import { Toaster } from 'svelte-sonner';
  import '../app.css';

  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 5 * 60 * 1000,
        retry: 2,
        refetchOnWindowFocus: false,
      },
    },
  });

  let { children } = $props();
</script>

<QueryClientProvider client={queryClient}>
  {@render children()}
</QueryClientProvider>

<Toaster 
  theme="dark" 
  position="top-right" 
  richColors 
  toastOptions={{ 
    classNames: { toast: 'glass border-slate-700' } 
  }} 
/>
```

### 4.4 Query & Mutation Hooks

#### Companies (src/lib/api/queries/companies.ts)
```typescript
import { createQuery, createMutation, useQueryClient } from '@tanstack/svelte-query';
import { api } from '../client';

export function useCompany(companyId: string) {
  return createQuery({
    queryKey: ['company', companyId],
    queryFn: async () => {
      const { data, error } = await api.GET('/company/{company_id}', {
        params: { path: { company_id: companyId } },
      });
      if (error) throw new Error(error.error_message);
      return data;
    },
    enabled: !!companyId,
  });
}

export function useRegisterCompany() {
  return createMutation({
    mutationFn: async (payload: {
      company_name: string;
      email: string;
      password: string;
      industry: string;
      size: string;
      website?: string;
      phone?: string;
    }) => {
      const { data, error } = await api.POST('/company/register', { body: payload });
      if (error) throw new Error(error.error_message);
      return data;
    },
    onSuccess: (data) => {
      // Store credentials for all future API calls
      localStorage.setItem('workspace-id', data.data.workspace_id);
      localStorage.setItem('user-id', data.data.user_id);
      localStorage.setItem('company-id', data.data.company_id);
    },
  });
}
```

#### Jobs (src/lib/api/queries/jobs.ts)
```typescript
import { createQuery, createMutation, useQueryClient } from '@tanstack/svelte-query';
import { api } from '../client';

export function useJobRequirements(companyId: string) {
  return createQuery({
    queryKey: ['jobs', companyId],
    queryFn: async () => {
      const { data, error } = await api.GET('/job-requirements/company/{company_id}', {
        params: { path: { company_id: companyId } },
      });
      if (error) throw new Error(error.error_message);
      return data;
    },
    enabled: !!companyId,
  });
}

export function useJobRequirement(jobId: string) {
  return createQuery({
    queryKey: ['job', jobId],
    queryFn: async () => {
      const { data, error } = await api.GET('/job-requirements/{job_requirement_id}', {
        params: { path: { job_requirement_id: jobId } },
      });
      if (error) throw new Error(error.error_message);
      return data;
    },
    enabled: !!jobId,
  });
}

export function useCreateJobRequirement() {
  const queryClient = useQueryClient();
  
  return createMutation({
    mutationFn: async (payload: {
      companyId: string;
      body: {
        title: string;
        department: string;
        description: string;
        requirements: Array<{ skill: string; level: string; required?: boolean }>;
        experience?: { min_years: number; max_years: number };
        location?: string;
        job_type?: string;
        salary_range?: { min: number; max: number; currency?: string };
        benefits?: string[];
      };
    }) => {
      const { data, error } = await api.POST('/job-requirements/company/{company_id}', {
        params: { path: { company_id: payload.companyId } },
        body: payload.body,
      });
      if (error) throw new Error(error.error_message);
      return data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['jobs', variables.companyId] });
    },
  });
}
```

#### Candidates (src/lib/api/queries/candidates.ts)
```typescript
import { createQuery, createMutation, useQueryClient } from '@tanstack/svelte-query';
import { api } from '../client';

export function useCandidates(jobId: string) {
  return createQuery({
    queryKey: ['candidates', jobId],
    queryFn: async () => {
      const { data, error } = await api.GET('/candidates/job/{job_requirement_id}', {
        params: { path: { job_requirement_id: jobId } },
      });
      if (error) throw new Error(error.error_message);
      return data;
    },
    enabled: !!jobId,
  });
}

export function useSelectTopResumes() {
  const queryClient = useQueryClient();
  
  return createMutation({
    mutationFn: async (payload: { jobId: string; topN: number }) => {
      const { data, error } = await api.POST('/candidates/{job_requirement_id}/select-top-resumes', {
        params: { 
          path: { job_requirement_id: payload.jobId },
          query: { top_n: payload.topN },
        },
      });
      if (error) throw new Error(error.error_message);
      return data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['candidates', variables.jobId] });
    },
  });
}
```

---

## 5. STEP 1: COMPANY REGISTRATION

### 5.1 Auth Store (src/lib/stores/auth.svelte.ts)

```typescript
class AuthStore {
  isAuthenticated = $state(false);
  companyId = $state<string | null>(null);
  workspaceId = $state<string | null>(null);
  userId = $state<string | null>(null);
  company = $state<Company | null>(null);
  isLoading = $state(true);

  constructor() {
    // Hydrate from localStorage on init
    if (typeof window !== 'undefined') {
      this.companyId = localStorage.getItem('company-id');
      this.workspaceId = localStorage.getItem('workspace-id');
      this.userId = localStorage.getItem('user-id');
      this.isAuthenticated = !!(this.companyId && this.workspaceId && this.userId);
      this.isLoading = false;
    }
  }

  setCredentials(data: { company_id: string; workspace_id: string; user_id: string }) {
    this.companyId = data.company_id;
    this.workspaceId = data.workspace_id;
    this.userId = data.user_id;
    this.isAuthenticated = true;
    
    localStorage.setItem('company-id', data.company_id);
    localStorage.setItem('workspace-id', data.workspace_id);
    localStorage.setItem('user-id', data.user_id);
  }

  logout() {
    this.isAuthenticated = false;
    this.companyId = null;
    this.workspaceId = null;
    this.userId = null;
    this.company = null;
    
    localStorage.removeItem('company-id');
    localStorage.removeItem('workspace-id');
    localStorage.removeItem('user-id');
  }
}

export const authStore = new AuthStore();
```

### 5.2 Registration Page (src/routes/(auth)/register/+page.svelte)

```svelte
<script lang="ts">
  import { goto } from '$app/navigation';
  import { useRegisterCompany } from '$lib/api/queries/companies';
  import { authStore } from '$lib/stores/auth.svelte';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import { Label } from '$lib/components/ui/label';
  import * as Select from '$lib/components/ui/select';
  import { toast } from 'svelte-sonner';
  import { Building2, Mail, Lock, Globe, Phone, Users } from 'lucide-svelte';

  let formData = $state({
    company_name: '',
    email: '',
    password: '',
    confirm_password: '',
    industry: '',
    size: '',
    website: '',
    phone: '',
  });

  const registerMutation = useRegisterCompany();

  async function handleSubmit(e: Event) {
    e.preventDefault();
    
    if (formData.password !== formData.confirm_password) {
      toast.error('Passwords do not match');
      return;
    }

    try {
      const result = await $registerMutation.mutateAsync({
        company_name: formData.company_name,
        email: formData.email,
        password: formData.password,
        industry: formData.industry,
        size: formData.size,
        website: formData.website || undefined,
        phone: formData.phone || undefined,
      });

      authStore.setCredentials(result.data);
      toast.success('Company registered successfully!');
      goto('/'); // Redirect to dashboard
    } catch (error) {
      toast.error(error.message || 'Registration failed');
    }
  }

  const industries = [
    'Technology', 'Finance', 'Healthcare', 'Manufacturing', 
    'Retail', 'Education', 'Consulting', 'Other'
  ];
  
  const companySizes = [
    { value: '1-10', label: '1-10 employees' },
    { value: '11-50', label: '11-50 employees' },
    { value: '51-200', label: '51-200 employees' },
    { value: '201-500', label: '201-500 employees' },
    { value: '501-1000', label: '501-1000 employees' },
    { value: '1001+', label: '1000+ employees' },
  ];
</script>

<div class="min-h-screen bg-obsidian-950 flex items-center justify-center p-4">
  <div class="w-full max-w-lg">
    <!-- Logo/Header -->
    <div class="text-center mb-8">
      <h1 class="text-3xl font-bold text-slate-100">HR Automation</h1>
      <p class="text-slate-400 mt-2">Register your company to get started</p>
    </div>

    <!-- Registration Form -->
    <form onsubmit={handleSubmit} class="card-executive p-8 space-y-6">
      <div class="grid gap-4">
        <!-- Company Name -->
        <div class="space-y-2">
          <Label for="company_name" class="text-slate-300">Company Name *</Label>
          <div class="relative">
            <Building2 class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <Input 
              id="company_name"
              bind:value={formData.company_name}
              placeholder="Acme Corporation"
              class="pl-10 bg-obsidian-850 border-slate-700"
              required
            />
          </div>
        </div>

        <!-- Email -->
        <div class="space-y-2">
          <Label for="email" class="text-slate-300">Email *</Label>
          <div class="relative">
            <Mail class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <Input 
              id="email"
              type="email"
              bind:value={formData.email}
              placeholder="hr@company.com"
              class="pl-10 bg-obsidian-850 border-slate-700"
              required
            />
          </div>
        </div>

        <!-- Password -->
        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-2">
            <Label for="password" class="text-slate-300">Password *</Label>
            <div class="relative">
              <Lock class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <Input 
                id="password"
                type="password"
                bind:value={formData.password}
                placeholder="••••••••"
                class="pl-10 bg-obsidian-850 border-slate-700"
                required
                minlength="8"
              />
            </div>
          </div>
          <div class="space-y-2">
            <Label for="confirm_password" class="text-slate-300">Confirm *</Label>
            <Input 
              id="confirm_password"
              type="password"
              bind:value={formData.confirm_password}
              placeholder="••••••••"
              class="bg-obsidian-850 border-slate-700"
              required
            />
          </div>
        </div>

        <!-- Industry & Size -->
        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-2">
            <Label class="text-slate-300">Industry *</Label>
            <Select.Root bind:value={formData.industry}>
              <Select.Trigger class="bg-obsidian-850 border-slate-700">
                <Select.Value placeholder="Select industry" />
              </Select.Trigger>
              <Select.Content class="bg-obsidian-900 border-slate-700">
                {#each industries as industry}
                  <Select.Item value={industry}>{industry}</Select.Item>
                {/each}
              </Select.Content>
            </Select.Root>
          </div>
          <div class="space-y-2">
            <Label class="text-slate-300">Company Size *</Label>
            <Select.Root bind:value={formData.size}>
              <Select.Trigger class="bg-obsidian-850 border-slate-700">
                <Select.Value placeholder="Select size" />
              </Select.Trigger>
              <Select.Content class="bg-obsidian-900 border-slate-700">
                {#each companySizes as size}
                  <Select.Item value={size.value}>{size.label}</Select.Item>
                {/each}
              </Select.Content>
            </Select.Root>
          </div>
        </div>

        <!-- Optional Fields -->
        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-2">
            <Label for="website" class="text-slate-300">Website</Label>
            <div class="relative">
              <Globe class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <Input 
                id="website"
                bind:value={formData.website}
                placeholder="https://company.com"
                class="pl-10 bg-obsidian-850 border-slate-700"
              />
            </div>
          </div>
          <div class="space-y-2">
            <Label for="phone" class="text-slate-300">Phone</Label>
            <div class="relative">
              <Phone class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <Input 
                id="phone"
                bind:value={formData.phone}
                placeholder="+1 234 567 8900"
                class="pl-10 bg-obsidian-850 border-slate-700"
              />
            </div>
          </div>
        </div>
      </div>

      <Button 
        type="submit" 
        class="w-full bg-info hover:bg-info/90"
        disabled={$registerMutation.isPending}
      >
        {$registerMutation.isPending ? 'Registering...' : 'Register Company'}
      </Button>

      <p class="text-center text-sm text-slate-500">
        Already have an account? 
        <a href="/login" class="text-info hover:underline">Sign in</a>
      </p>
    </form>
  </div>
</div>
```

---

## 6. STEP 2: CREATE JOB REQUIREMENTS

### 6.1 Job Form Component (src/lib/components/jobs/JobForm.svelte)

```svelte
<script lang="ts">
  import { useCreateJobRequirement } from '$lib/api/queries/jobs';
  import { authStore } from '$lib/stores/auth.svelte';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import { Label } from '$lib/components/ui/label';
  import { Textarea } from '$lib/components/ui/textarea';
  import * as Select from '$lib/components/ui/select';
  import SkillsInput from './SkillsInput.svelte';
  import { toast } from 'svelte-sonner';
  import { goto } from '$app/navigation';
  import { Plus, X } from 'lucide-svelte';

  let formData = $state({
    title: '',
    department: '',
    description: '',
    requirements: [] as Array<{ skill: string; level: string; required: boolean }>,
    experience: { min_years: 0, max_years: 5 },
    location: '',
    job_type: 'full-time',
    salary_range: { min: 0, max: 0, currency: 'USD' },
    benefits: [] as string[],
  });

  let newBenefit = $state('');

  const createJobMutation = useCreateJobRequirement();

  async function handleSubmit(e: Event) {
    e.preventDefault();
    
    if (!authStore.companyId) {
      toast.error('Company not found. Please login again.');
      return;
    }

    if (formData.requirements.length === 0) {
      toast.error('Please add at least one skill requirement');
      return;
    }

    try {
      await $createJobMutation.mutateAsync({
        companyId: authStore.companyId,
        body: {
          title: formData.title,
          department: formData.department,
          description: formData.description,
          requirements: formData.requirements,
          experience: formData.experience,
          location: formData.location,
          job_type: formData.job_type,
          salary_range: formData.salary_range.min > 0 ? formData.salary_range : undefined,
          benefits: formData.benefits.length > 0 ? formData.benefits : undefined,
        },
      });

      toast.success('Job requirement created!');
      goto('/jobs');
    } catch (error) {
      toast.error(error.message || 'Failed to create job');
    }
  }

  function addBenefit() {
    if (newBenefit.trim()) {
      formData.benefits = [...formData.benefits, newBenefit.trim()];
      newBenefit = '';
    }
  }

  function removeBenefit(index: number) {
    formData.benefits = formData.benefits.filter((_, i) => i !== index);
  }

  const jobTypes = ['full-time', 'part-time', 'contract', 'internship'];
  const skillLevels = ['beginner', 'intermediate', 'advanced', 'expert'];
</script>

<form onsubmit={handleSubmit} class="space-y-8">
  <!-- Basic Info -->
  <div class="card-executive p-6 space-y-4">
    <h3 class="text-lg font-semibold text-slate-100">Basic Information</h3>
    
    <div class="grid grid-cols-2 gap-4">
      <div class="space-y-2">
        <Label class="text-slate-300">Job Title *</Label>
        <Input 
          bind:value={formData.title}
          placeholder="Senior Software Engineer"
          class="bg-obsidian-850 border-slate-700"
          required
        />
      </div>
      <div class="space-y-2">
        <Label class="text-slate-300">Department *</Label>
        <Input 
          bind:value={formData.department}
          placeholder="Engineering"
          class="bg-obsidian-850 border-slate-700"
          required
        />
      </div>
    </div>

    <div class="space-y-2">
      <Label class="text-slate-300">Description *</Label>
      <Textarea 
        bind:value={formData.description}
        placeholder="Describe the role, responsibilities, and what you're looking for..."
        class="bg-obsidian-850 border-slate-700 min-h-32"
        required
      />
    </div>

    <div class="grid grid-cols-3 gap-4">
      <div class="space-y-2">
        <Label class="text-slate-300">Location</Label>
        <Input 
          bind:value={formData.location}
          placeholder="Remote / New York, NY"
          class="bg-obsidian-850 border-slate-700"
        />
      </div>
      <div class="space-y-2">
        <Label class="text-slate-300">Job Type</Label>
        <Select.Root bind:value={formData.job_type}>
          <Select.Trigger class="bg-obsidian-850 border-slate-700">
            <Select.Value />
          </Select.Trigger>
          <Select.Content class="bg-obsidian-900 border-slate-700">
            {#each jobTypes as type}
              <Select.Item value={type} class="capitalize">{type}</Select.Item>
            {/each}
          </Select.Content>
        </Select.Root>
      </div>
      <div class="space-y-2">
        <Label class="text-slate-300">Experience (Years)</Label>
        <div class="flex gap-2">
          <Input 
            type="number"
            bind:value={formData.experience.min_years}
            placeholder="Min"
            class="bg-obsidian-850 border-slate-700"
            min="0"
          />
          <span class="text-slate-500 self-center">to</span>
          <Input 
            type="number"
            bind:value={formData.experience.max_years}
            placeholder="Max"
            class="bg-obsidian-850 border-slate-700"
            min="0"
          />
        </div>
      </div>
    </div>
  </div>

  <!-- Skills Requirements -->
  <div class="card-executive p-6 space-y-4">
    <h3 class="text-lg font-semibold text-slate-100">Skill Requirements *</h3>
    <SkillsInput 
      bind:skills={formData.requirements}
      levels={skillLevels}
    />
  </div>

  <!-- Salary & Benefits -->
  <div class="card-executive p-6 space-y-4">
    <h3 class="text-lg font-semibold text-slate-100">Compensation</h3>
    
    <div class="grid grid-cols-3 gap-4">
      <div class="space-y-2">
        <Label class="text-slate-300">Min Salary</Label>
        <Input 
          type="number"
          bind:value={formData.salary_range.min}
          placeholder="50000"
          class="bg-obsidian-850 border-slate-700"
        />
      </div>
      <div class="space-y-2">
        <Label class="text-slate-300">Max Salary</Label>
        <Input 
          type="number"
          bind:value={formData.salary_range.max}
          placeholder="80000"
          class="bg-obsidian-850 border-slate-700"
        />
      </div>
      <div class="space-y-2">
        <Label class="text-slate-300">Currency</Label>
        <Select.Root bind:value={formData.salary_range.currency}>
          <Select.Trigger class="bg-obsidian-850 border-slate-700">
            <Select.Value />
          </Select.Trigger>
          <Select.Content class="bg-obsidian-900 border-slate-700">
            <Select.Item value="USD">USD</Select.Item>
            <Select.Item value="EUR">EUR</Select.Item>
            <Select.Item value="GBP">GBP</Select.Item>
            <Select.Item value="INR">INR</Select.Item>
          </Select.Content>
        </Select.Root>
      </div>
    </div>

    <!-- Benefits -->
    <div class="space-y-2">
      <Label class="text-slate-300">Benefits</Label>
      <div class="flex gap-2">
        <Input 
          bind:value={newBenefit}
          placeholder="Health insurance, 401k, etc."
          class="bg-obsidian-850 border-slate-700"
          onkeydown={(e) => e.key === 'Enter' && (e.preventDefault(), addBenefit())}
        />
        <Button type="button" variant="outline" onclick={addBenefit}>
          <Plus class="w-4 h-4" />
        </Button>
      </div>
      {#if formData.benefits.length > 0}
        <div class="flex flex-wrap gap-2 mt-2">
          {#each formData.benefits as benefit, i}
            <span class="inline-flex items-center gap-1 px-3 py-1 bg-slate-800 rounded-full text-sm text-slate-300">
              {benefit}
              <button type="button" onclick={() => removeBenefit(i)} class="text-slate-500 hover:text-slate-300">
                <X class="w-3 h-3" />
              </button>
            </span>
          {/each}
        </div>
      {/if}
    </div>
  </div>

  <div class="flex justify-end gap-4">
    <Button type="button" variant="ghost" onclick={() => goto('/jobs')}>
      Cancel
    </Button>
    <Button type="submit" class="bg-info hover:bg-info/90" disabled={$createJobMutation.isPending}>
      {$createJobMutation.isPending ? 'Creating...' : 'Create Job Requirement'}
    </Button>
  </div>
</form>
```

---

## 7. STEP 3: DASHBOARD (Data Populated)

### 7.1 Dashboard Overview (src/routes/(dashboard)/+page.svelte)

```svelte
<script lang="ts">
  import { authStore } from '$lib/stores/auth.svelte';
  import { useCompany } from '$lib/api/queries/companies';
  import { useJobRequirements } from '$lib/api/queries/jobs';
  import StatCard from '$lib/components/dashboard/StatCard.svelte';
  import JobsOverview from '$lib/components/dashboard/JobsOverview.svelte';
  import RecentCandidates from '$lib/components/dashboard/RecentCandidates.svelte';
  import { Skeleton } from '$lib/components/ui/skeleton';
  import { Button } from '$lib/components/ui/button';
  import { Plus, Briefcase, Users, Video, CheckCircle } from 'lucide-svelte';

  const companyQuery = useCompany(authStore.companyId!);
  const jobsQuery = useJobRequirements(authStore.companyId!);

  // Derived stats from jobs data
  let stats = $derived.by(() => {
    if (!$jobsQuery.data?.data) return null;
    const jobs = $jobsQuery.data.data;
    return {
      totalJobs: jobs.length,
      activeJobs: jobs.filter(j => j.status === 'active').length,
      totalCandidates: jobs.reduce((acc, j) => acc + (j.candidate_count || 0), 0),
      interviewsCompleted: jobs.reduce((acc, j) => acc + (j.interviews_completed || 0), 0),
    };
  });
</script>

<div class="space-y-8">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold text-slate-100">
        {#if $companyQuery.isLoading}
          <Skeleton class="h-8 w-48" />
        {:else}
          Welcome back, {$companyQuery.data?.data?.company_name}
        {/if}
      </h1>
      <p class="text-slate-400 mt-1">Here's what's happening with your hiring</p>
    </div>
    <Button href="/jobs/new" class="bg-info hover:bg-info/90">
      <Plus class="w-4 h-4 mr-2" />
      New Job Posting
    </Button>
  </div>

  <!-- Stats Grid -->
  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
    {#if $jobsQuery.isLoading}
      {#each Array(4) as _}
        <div class="card-executive p-6">
          <Skeleton class="h-4 w-24 mb-2" />
          <Skeleton class="h-8 w-16" />
        </div>
      {/each}
    {:else if stats}
      <StatCard 
        title="Active Jobs" 
        value={stats.activeJobs}
        subtitle="{stats.totalJobs} total"
        icon={Briefcase}
        iconColor="text-info"
      />
      <StatCard 
        title="Total Candidates" 
        value={stats.totalCandidates}
        icon={Users}
        iconColor="text-purple-400"
      />
      <StatCard 
        title="Interviews" 
        value={stats.interviewsCompleted}
        subtitle="Completed"
        icon={Video}
        iconColor="text-amber-400"
      />
      <StatCard 
        title="Hired" 
        value={0}
        subtitle="This month"
        icon={CheckCircle}
        iconColor="text-success"
      />
    {/if}
  </div>

  <!-- Jobs Overview -->
  <div class="card-executive p-6">
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-lg font-semibold text-slate-100">Job Requirements</h2>
      <Button variant="ghost" href="/jobs" class="text-slate-400">View all</Button>
    </div>
    
    {#if $jobsQuery.isLoading}
      <div class="space-y-4">
        {#each Array(3) as _}
          <Skeleton class="h-20 w-full" />
        {/each}
      </div>
    {:else if $jobsQuery.data?.data?.length === 0}
      <div class="text-center py-12">
        <Briefcase class="w-12 h-12 text-slate-600 mx-auto mb-4" />
        <h3 class="text-lg font-medium text-slate-300">No job requirements yet</h3>
        <p class="text-slate-500 mt-1">Create your first job posting to start receiving candidates</p>
        <Button href="/jobs/new" class="mt-4 bg-info hover:bg-info/90">
          <Plus class="w-4 h-4 mr-2" />
          Create Job Requirement
        </Button>
      </div>
    {:else}
      <JobsOverview jobs={$jobsQuery.data.data} />
    {/if}
  </div>

  <!-- Recent Candidates -->
  <div class="card-executive p-6">
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-lg font-semibold text-slate-100">Recent Candidates</h2>
      <Button variant="ghost" href="/candidates" class="text-slate-400">View all</Button>
    </div>
    <RecentCandidates companyId={authStore.companyId!} />
  </div>
</div>
```

### 7.2 Jobs Overview Component (src/lib/components/dashboard/JobsOverview.svelte)

```svelte
<script lang="ts">
  import StatusBadge from '$lib/components/shared/StatusBadge.svelte';
  import { Button } from '$lib/components/ui/button';
  import { formatDate } from '$lib/utils/format';
  import { Users, ChevronRight } from 'lucide-svelte';

  let { jobs } = $props<{ jobs: Job[] }>();
</script>

<div class="space-y-3">
  {#each jobs.slice(0, 5) as job (job.job_requirement_id)}
    <a 
      href="/jobs/{job.job_requirement_id}" 
      class="flex items-center justify-between p-4 rounded-lg bg-obsidian-850 hover:bg-obsidian-800 transition-colors group"
    >
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-3">
          <h4 class="font-medium text-slate-200 truncate">{job.title}</h4>
          <StatusBadge status={job.status} />
        </div>
        <p class="text-sm text-slate-500 mt-1">
          {job.department} • {job.location || 'Remote'} • Posted {formatDate(job.created_at)}
        </p>
      </div>
      
      <div class="flex items-center gap-6">
        <div class="text-right">
          <div class="flex items-center gap-1 text-slate-300">
            <Users class="w-4 h-4 text-slate-500" />
            <span class="font-medium">{job.candidate_count || 0}</span>
          </div>
          <p class="text-xs text-slate-500">Candidates</p>
        </div>
        <ChevronRight class="w-5 h-5 text-slate-600 group-hover:text-slate-400 transition-colors" />
      </div>
    </a>
  {/each}
</div>
```

---

## 8. MEDIA HANDLING — VIDEO & AUDIO

### 8.1 Media Store (src/lib/stores/media.svelte.ts)

```typescript
type PermissionStatus = 'prompt' | 'granted' | 'denied' | 'error';

class MediaStore {
  stream = $state<MediaStream | null>(null);
  videoEnabled = $state(true);
  audioEnabled = $state(true);
  permissionStatus = $state<PermissionStatus>('prompt');
  errorMessage = $state<string | null>(null);
  audioLevel = $state(0);
  
  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private animationFrame: number | null = null;

  async initialize() {
    try {
      this.permissionStatus = 'prompt';
      this.errorMessage = null;
      
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 1280, height: 720, facingMode: 'user' },
        audio: { echoCancellation: true, noiseSuppression: true },
      });
      
      this.stream = stream;
      this.permissionStatus = 'granted';
      this.setupAudioAnalysis(stream);
      
    } catch (err) {
      this.permissionStatus = 'denied';
      if (err instanceof DOMException) {
        if (err.name === 'NotAllowedError') {
          this.errorMessage = 'Camera/microphone access denied. Please enable in browser settings.';
        } else if (err.name === 'NotFoundError') {
          this.errorMessage = 'No camera or microphone found on this device.';
        } else {
          this.errorMessage = `Media error: ${err.message}`;
        }
      }
    }
  }

  private setupAudioAnalysis(stream: MediaStream) {
    this.audioContext = new AudioContext();
    const source = this.audioContext.createMediaStreamSource(stream);
    this.analyser = this.audioContext.createAnalyser();
    this.analyser.fftSize = 256;
    source.connect(this.analyser);
    
    const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
    
    const updateLevel = () => {
      if (!this.analyser) return;
      this.analyser.getByteFrequencyData(dataArray);
      const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
      this.audioLevel = Math.min(average / 128, 1);
      this.animationFrame = requestAnimationFrame(updateLevel);
    };
    updateLevel();
  }

  toggleVideo() {
    if (!this.stream) return;
    const videoTrack = this.stream.getVideoTracks()[0];
    if (videoTrack) {
      videoTrack.enabled = !videoTrack.enabled;
      this.videoEnabled = videoTrack.enabled;
    }
  }

  toggleAudio() {
    if (!this.stream) return;
    const audioTrack = this.stream.getAudioTracks()[0];
    if (audioTrack) {
      audioTrack.enabled = !audioTrack.enabled;
      this.audioEnabled = audioTrack.enabled;
    }
  }

  cleanup() {
    if (this.animationFrame) cancelAnimationFrame(this.animationFrame);
    if (this.audioContext) this.audioContext.close();
    if (this.stream) this.stream.getTracks().forEach(t => t.stop());
    this.stream = null;
  }
}

export const mediaStore = new MediaStore();
```

### 5.2 Video Preview Component (src/lib/components/interview/VideoPreview.svelte)

```svelte
<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { mediaStore } from '$lib/stores/media.svelte';
  import { Video, VideoOff, AlertCircle } from 'lucide-svelte';

  let videoElement: HTMLVideoElement;

  onMount(() => {
    mediaStore.initialize();
  });

  onDestroy(() => {
    mediaStore.cleanup();
  });

  $effect(() => {
    if (videoElement && mediaStore.stream) {
      videoElement.srcObject = mediaStore.stream;
    }
  });
</script>

<div class="relative aspect-video rounded-lg overflow-hidden bg-obsidian-900 border border-slate-800">
  {#if mediaStore.permissionStatus === 'granted' && mediaStore.videoEnabled}
    <video
      bind:this={videoElement}
      autoplay
      playsinline
      muted
      class="w-full h-full object-cover scale-x-[-1]"
    />
    <!-- Vignette overlay -->
    <div class="absolute inset-0 bg-gradient-to-t from-obsidian-950/60 via-transparent to-obsidian-950/30 pointer-events-none" />
    
  {:else if mediaStore.permissionStatus === 'denied'}
    <div class="absolute inset-0 flex flex-col items-center justify-center gap-4 p-6 text-center">
      <div class="p-4 rounded-full bg-error/10">
        <AlertCircle class="w-10 h-10 text-error" />
      </div>
      <p class="text-slate-400 text-sm max-w-xs">{mediaStore.errorMessage}</p>
    </div>
    
  {:else if !mediaStore.videoEnabled}
    <div class="absolute inset-0 flex items-center justify-center">
      <div class="p-6 rounded-full bg-slate-800/50">
        <VideoOff class="w-12 h-12 text-slate-500" />
      </div>
    </div>
    
  {:else}
    <div class="absolute inset-0 flex items-center justify-center">
      <div class="w-10 h-10 border-2 border-silver border-t-transparent rounded-full animate-spin" />
    </div>
  {/if}
  
  <!-- Name badge -->
  <div class="absolute bottom-3 left-3 px-3 py-1.5 glass rounded-md">
    <span class="text-sm font-medium text-slate-200">You</span>
  </div>
</div>
```

### 5.3 Audio Visualizer (src/lib/components/interview/AudioVisualizer.svelte)

```svelte
<script lang="ts">
  import { mediaStore } from '$lib/stores/media.svelte';
  import { Mic, MicOff } from 'lucide-svelte';

  const BAR_COUNT = 5;
  
  let bars = $derived(
    Array.from({ length: BAR_COUNT }, (_, i) => {
      const base = mediaStore.audioLevel * 100;
      const variance = Math.sin(Date.now() / 100 + i) * 10;
      return Math.max(15, Math.min(100, base + variance * (mediaStore.audioEnabled ? 1 : 0)));
    })
  );
</script>

<div class="flex items-center gap-2">
  <div class="p-2 rounded-lg {mediaStore.audioEnabled ? 'bg-success/10' : 'bg-slate-800'}">
    {#if mediaStore.audioEnabled}
      <Mic class="w-4 h-4 text-success" />
    {:else}
      <MicOff class="w-4 h-4 text-slate-500" />
    {/if}
  </div>
  
  <div class="flex items-end gap-0.5 h-6">
    {#each bars as height, i}
      <div
        class="w-1 rounded-full transition-all duration-75 {mediaStore.audioEnabled ? 'bg-success' : 'bg-slate-600'}"
        style="height: {height}%"
      />
    {/each}
  </div>
</div>
```

---

## 9. REAL-TIME TRANSCRIPT SYSTEM

### 9.1 Interview Store (src/lib/stores/interview.svelte.ts)

```typescript
type TranscriptEntry = {
  id: string;
  role: 'interviewer' | 'candidate';
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
};

type InterviewStatus = 'idle' | 'connecting' | 'active' | 'completed' | 'error';

class InterviewStore {
  status = $state<InterviewStatus>('idle');
  transcript = $state<TranscriptEntry[]>([]);
  currentStreamText = $state('');
  elapsedSeconds = $state(0);
  
  private ws: WebSocket | null = null;
  private timerInterval: number | null = null;
  private reconnectAttempts = 0;

  connect(sessionId: string, type: 'technical' | 'hr') {
    const port = type === 'technical' ? 8100 : 8200;
    const url = `ws://localhost:${port}/ws/interview/${sessionId}`;
    
    this.status = 'connecting';
    this.ws = new WebSocket(url);
    
    this.ws.onopen = () => {
      this.status = 'active';
      this.reconnectAttempts = 0;
      this.startTimer();
    };
    
    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      this.handleMessage(msg);
    };
    
    this.ws.onclose = () => {
      if (this.status === 'active' && this.reconnectAttempts < 3) {
        this.reconnectAttempts++;
        setTimeout(() => this.connect(sessionId, type), 2000 * this.reconnectAttempts);
      } else if (this.status !== 'completed') {
        this.status = 'error';
      }
    };
    
    this.ws.onerror = () => {
      this.status = 'error';
    };
  }

  private handleMessage(msg: { type: string; data: unknown }) {
    switch (msg.type) {
      case 'transcript_chunk':
        // Streaming text effect
        this.currentStreamText += (msg.data as { text: string }).text;
        break;
        
      case 'transcript_complete':
        const entry = msg.data as { role: string; content: string };
        this.transcript.push({
          id: crypto.randomUUID(),
          role: entry.role as 'interviewer' | 'candidate',
          content: entry.content,
          timestamp: new Date(),
        });
        this.currentStreamText = '';
        break;
        
      case 'interview_ended':
        this.status = 'completed';
        this.stopTimer();
        break;
    }
  }

  private startTimer() {
    this.timerInterval = setInterval(() => {
      this.elapsedSeconds++;
    }, 1000) as unknown as number;
  }

  private stopTimer() {
    if (this.timerInterval) clearInterval(this.timerInterval);
  }

  endInterview() {
    this.ws?.send(JSON.stringify({ type: 'end_interview' }));
    this.status = 'completed';
    this.stopTimer();
  }

  cleanup() {
    this.ws?.close();
    this.stopTimer();
    this.transcript = [];
    this.status = 'idle';
  }
}

export const interviewStore = new InterviewStore();
```

### 6.2 Transcript Panel (src/lib/components/interview/TranscriptPanel.svelte)

```svelte
<script lang="ts">
  import { interviewStore } from '$lib/stores/interview.svelte';
  import { Bot, User } from 'lucide-svelte';

  let container: HTMLDivElement;

  // Auto-scroll on new messages
  $effect(() => {
    if (interviewStore.transcript.length || interviewStore.currentStreamText) {
      container?.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
    }
  });
</script>

<div class="card-executive h-full flex flex-col">
  <div class="px-4 py-3 border-b border-slate-800">
    <h3 class="text-sm font-semibold text-slate-300 uppercase tracking-wider">
      AI Transcript
    </h3>
  </div>
  
  <div bind:this={container} class="flex-1 overflow-y-auto p-4 space-y-4">
    {#each interviewStore.transcript as entry (entry.id)}
      <div class="flex gap-3 {entry.role === 'interviewer' ? '' : 'flex-row-reverse'}">
        <div class="shrink-0 w-8 h-8 rounded-full flex items-center justify-center 
          {entry.role === 'interviewer' ? 'bg-info/10' : 'bg-slate-800'}">
          {#if entry.role === 'interviewer'}
            <Bot class="w-4 h-4 text-info" />
          {:else}
            <User class="w-4 h-4 text-slate-400" />
          {/if}
        </div>
        
        <div class="max-w-[80%] px-4 py-3 rounded-lg 
          {entry.role === 'interviewer' ? 'bg-slate-800/50' : 'bg-obsidian-850'}">
          <p class="text-sm text-slate-300 leading-relaxed">{entry.content}</p>
          <span class="text-xs text-slate-500 mt-1 block">
            {entry.timestamp.toLocaleTimeString()}
          </span>
        </div>
      </div>
    {/each}
    
    <!-- Streaming text indicator -->
    {#if interviewStore.currentStreamText}
      <div class="flex gap-3">
        <div class="shrink-0 w-8 h-8 rounded-full bg-info/10 flex items-center justify-center">
          <Bot class="w-4 h-4 text-info animate-pulse" />
        </div>
        <div class="max-w-[80%] px-4 py-3 rounded-lg bg-slate-800/50">
          <p class="text-sm text-slate-300 leading-relaxed">
            {interviewStore.currentStreamText}
            <span class="inline-block w-2 h-4 bg-info/50 ml-0.5 animate-pulse" />
          </p>
        </div>
      </div>
    {/if}
  </div>
</div>
```

---

## 10. CONTROL BAR (GLASSMORPHIC)

### 10.1 Component (src/lib/components/interview/ControlBar.svelte)

```svelte
<script lang="ts">
  import { mediaStore } from '$lib/stores/media.svelte';
  import { interviewStore } from '$lib/stores/interview.svelte';
  import { Video, VideoOff, Mic, MicOff, PhoneOff, Settings } from 'lucide-svelte';
  import * as Dialog from '$lib/components/ui/dialog';
  import { Button } from '$lib/components/ui/button';
  import AudioVisualizer from './AudioVisualizer.svelte';
  import InterviewTimer from './InterviewTimer.svelte';

  let showEndConfirm = $state(false);

  function handleEndInterview() {
    interviewStore.endInterview();
    showEndConfirm = false;
  }
</script>

<div class="glass rounded-2xl px-6 py-4 flex items-center justify-between">
  <!-- Left: Timer & Audio -->
  <div class="flex items-center gap-4">
    <InterviewTimer seconds={interviewStore.elapsedSeconds} />
    <div class="w-px h-8 bg-slate-700" />
    <AudioVisualizer />
  </div>
  
  <!-- Center: Primary Controls -->
  <div class="flex items-center gap-2">
    <button
      onclick={() => mediaStore.toggleAudio()}
      class="w-12 h-12 rounded-full flex items-center justify-center transition-all
        {mediaStore.audioEnabled 
          ? 'bg-slate-800 hover:bg-slate-700 text-slate-200' 
          : 'bg-error/20 text-error'}"
    >
      {#if mediaStore.audioEnabled}
        <Mic class="w-5 h-5" />
      {:else}
        <MicOff class="w-5 h-5" />
      {/if}
    </button>
    
    <button
      onclick={() => mediaStore.toggleVideo()}
      class="w-12 h-12 rounded-full flex items-center justify-center transition-all
        {mediaStore.videoEnabled 
          ? 'bg-slate-800 hover:bg-slate-700 text-slate-200' 
          : 'bg-error/20 text-error'}"
    >
      {#if mediaStore.videoEnabled}
        <Video class="w-5 h-5" />
      {:else}
        <VideoOff class="w-5 h-5" />
      {/if}
    </button>
    
    <button
      onclick={() => showEndConfirm = true}
      class="w-12 h-12 rounded-full bg-error hover:bg-error/90 text-white flex items-center justify-center transition-all"
    >
      <PhoneOff class="w-5 h-5" />
    </button>
  </div>
  
  <!-- Right: Settings -->
  <button class="w-10 h-10 rounded-lg bg-slate-800 hover:bg-slate-700 flex items-center justify-center text-slate-400">
    <Settings class="w-4 h-4" />
  </button>
</div>

<!-- End Confirmation Dialog -->
<Dialog.Root bind:open={showEndConfirm}>
  <Dialog.Content class="card-executive border-slate-700 max-w-md">
    <Dialog.Header>
      <Dialog.Title class="text-slate-100">End Interview?</Dialog.Title>
      <Dialog.Description class="text-slate-400">
        This will submit your interview for AI evaluation. This action cannot be undone.
      </Dialog.Description>
    </Dialog.Header>
    <Dialog.Footer class="gap-3">
      <Button variant="ghost" onclick={() => showEndConfirm = false}>
        Continue Interview
      </Button>
      <Button variant="destructive" onclick={handleEndInterview}>
        End Interview
      </Button>
    </Dialog.Footer>
  </Dialog.Content>
</Dialog.Root>
```

---

## 8. DASHBOARD — ROYAL DATA TABLE

### 8.1 Candidate Table (src/lib/components/dashboard/CandidateTable.svelte)

```svelte
<script lang="ts">
  import * as Table from '$lib/components/ui/table';
  import { Badge } from '$lib/components/ui/badge';
  import { Skeleton } from '$lib/components/ui/skeleton';
  import StatusBadge from '$lib/components/shared/StatusBadge.svelte';
  import ScoreGauge from '$lib/components/shared/ScoreGauge.svelte';
  import { formatDate } from '$lib/utils/format';
  import { ChevronRight } from 'lucide-svelte';

  let { candidates, isLoading = false } = $props<{
    candidates: Candidate[];
    isLoading?: boolean;
  }>();
</script>

<div class="card-executive overflow-hidden">
  <Table.Root>
    <Table.Header>
      <Table.Row class="bg-obsidian-850 hover:bg-obsidian-850 border-b border-slate-800">
        <Table.Head class="text-silver font-semibold">Candidate</Table.Head>
        <Table.Head class="text-silver font-semibold">Stage</Table.Head>
        <Table.Head class="text-silver font-semibold text-center">Aptitude</Table.Head>
        <Table.Head class="text-silver font-semibold text-center">Technical</Table.Head>
        <Table.Head class="text-silver font-semibold text-center">HR</Table.Head>
        <Table.Head class="text-silver font-semibold">Applied</Table.Head>
        <Table.Head />
      </Table.Row>
    </Table.Header>
    
    <Table.Body>
      {#if isLoading}
        {#each Array(5) as _}
          <Table.Row class="border-b border-slate-800/50">
            <Table.Cell>
              <div class="flex items-center gap-3">
                <Skeleton class="w-9 h-9 rounded-full" />
                <div class="space-y-1.5">
                  <Skeleton class="h-4 w-32" />
                  <Skeleton class="h-3 w-40" />
                </div>
              </div>
            </Table.Cell>
            <Table.Cell><Skeleton class="h-6 w-24" /></Table.Cell>
            <Table.Cell><Skeleton class="h-8 w-8 mx-auto rounded-full" /></Table.Cell>
            <Table.Cell><Skeleton class="h-8 w-8 mx-auto rounded-full" /></Table.Cell>
            <Table.Cell><Skeleton class="h-8 w-8 mx-auto rounded-full" /></Table.Cell>
            <Table.Cell><Skeleton class="h-4 w-20" /></Table.Cell>
            <Table.Cell />
          </Table.Row>
        {/each}
      {:else}
        {#each candidates as candidate (candidate.candidate_id)}
          <Table.Row class="border-b border-slate-800/50 hover:bg-obsidian-850/50 transition-colors cursor-pointer group">
            <Table.Cell>
              <div class="flex items-center gap-3">
                <div class="w-9 h-9 rounded-full bg-slate-800 flex items-center justify-center text-sm font-medium text-silver">
                  {candidate.first_name.charAt(0)}{candidate.last_name.charAt(0)}
                </div>
                <div>
                  <p class="font-medium text-slate-200">{candidate.first_name} {candidate.last_name}</p>
                  <p class="text-sm text-slate-500">{candidate.email}</p>
                </div>
              </div>
            </Table.Cell>
            <Table.Cell>
              <StatusBadge status={candidate.status} />
            </Table.Cell>
            <Table.Cell class="text-center">
              {#if candidate.aptitude_score}
                <ScoreGauge score={candidate.aptitude_score} size="sm" />
              {:else}
                <span class="text-slate-600">—</span>
              {/if}
            </Table.Cell>
            <Table.Cell class="text-center">
              {#if candidate.technical_score}
                <ScoreGauge score={candidate.technical_score} size="sm" />
              {:else}
                <span class="text-slate-600">—</span>
              {/if}
            </Table.Cell>
            <Table.Cell class="text-center">
              {#if candidate.hr_score}
                <ScoreGauge score={candidate.hr_score} size="sm" />
              {:else}
                <span class="text-slate-600">—</span>
              {/if}
            </Table.Cell>
            <Table.Cell class="text-slate-400 text-sm">
              {formatDate(candidate.created_at)}
            </Table.Cell>
            <Table.Cell>
              <ChevronRight class="w-4 h-4 text-slate-600 group-hover:text-silver transition-colors" />
            </Table.Cell>
          </Table.Row>
        {/each}
      {/if}
    </Table.Body>
  </Table.Root>
</div>
```

---

## 11. INTERVIEW DETAIL VIEW

Create a comprehensive detail view at `src/routes/(dashboard)/candidates/[id]/interview/[interview_id]/+page.svelte` that displays:

1. **Interview metadata** — Date, duration, AI model used
2. **Full transcript** — Scrollable, with speaker highlighting
3. **Score breakdown** — Radar chart for all metrics
4. **AI Analysis** — Strengths, weaknesses, recommendation
5. **Sentiment timeline** — Visual representation of confidence throughout

---

## 12. JOB DETAIL PAGE WITH CANDIDATE PIPELINE

### 12.1 Job Detail (src/routes/(dashboard)/jobs/[job_id]/+page.svelte)

```svelte
<script lang="ts">
  import { page } from '$app/stores';
  import { useJobRequirement } from '$lib/api/queries/jobs';
  import { useCandidates, useSelectTopResumes } from '$lib/api/queries/candidates';
  import { Button } from '$lib/components/ui/button';
  import * as Tabs from '$lib/components/ui/tabs';
  import CandidateTable from '$lib/components/dashboard/CandidateTable.svelte';
  import PipelineView from '$lib/components/candidates/PipelineView.svelte';
  import StatusBadge from '$lib/components/shared/StatusBadge.svelte';
  import { toast } from 'svelte-sonner';
  import { Brain, Users, FileText, Video, UserCheck, Settings } from 'lucide-svelte';

  const jobId = $derived($page.params.job_id);
  const jobQuery = useJobRequirement(jobId);
  const candidatesQuery = useCandidates(jobId);
  const selectTopMutation = useSelectTopResumes();

  let topN = $state(10);

  async function handleSelectTopResumes() {
    try {
      const result = await $selectTopMutation.mutateAsync({ jobId, topN });
      toast.success(`Selected top ${result.data.candidates_selected} candidates`, {
        description: 'Candidates have been shortlisted for aptitude test',
      });
    } catch (error) {
      toast.error(error.message);
    }
  }

  // Pipeline stage counts
  let stageCounts = $derived.by(() => {
    if (!$candidatesQuery.data?.data) return {};
    const candidates = $candidatesQuery.data.data;
    return {
      applied: candidates.filter(c => c.status === 'applied').length,
      aptitude_eligible: candidates.filter(c => c.status === 'aptitude_eligible').length,
      aptitude_passed: candidates.filter(c => c.status === 'aptitude_passed').length,
      technical_eligible: candidates.filter(c => c.status === 'technical_eligible').length,
      technical_passed: candidates.filter(c => c.status === 'technical_passed').length,
      hr_eligible: candidates.filter(c => c.status === 'hr_eligible').length,
      hr_passed: candidates.filter(c => c.status === 'hr_passed').length,
      rejected: candidates.filter(c => c.status === 'rejected').length,
    };
  });
</script>

<div class="space-y-6">
  <!-- Header -->
  {#if $jobQuery.data?.data}
    {@const job = $jobQuery.data.data}
    <div class="flex items-start justify-between">
      <div>
        <div class="flex items-center gap-3">
          <h1 class="text-2xl font-bold text-slate-100">{job.title}</h1>
          <StatusBadge status={job.status} />
        </div>
        <p class="text-slate-400 mt-1">{job.department} • {job.location || 'Remote'}</p>
      </div>
      <div class="flex gap-3">
        <Button variant="outline" href="/jobs/{jobId}/edit">
          <Settings class="w-4 h-4 mr-2" />
          Edit Job
        </Button>
      </div>
    </div>
  {/if}

  <!-- Pipeline Summary -->
  <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
    <div class="card-executive p-4 text-center">
      <p class="text-2xl font-bold text-slate-100">{stageCounts.applied || 0}</p>
      <p class="text-xs text-slate-500">Applied</p>
    </div>
    <div class="card-executive p-4 text-center">
      <p class="text-2xl font-bold text-info">{stageCounts.aptitude_eligible || 0}</p>
      <p class="text-xs text-slate-500">Aptitude Ready</p>
    </div>
    <div class="card-executive p-4 text-center">
      <p class="text-2xl font-bold text-purple-400">{stageCounts.aptitude_passed || 0}</p>
      <p class="text-xs text-slate-500">Aptitude Passed</p>
    </div>
    <div class="card-executive p-4 text-center">
      <p class="text-2xl font-bold text-amber-400">{stageCounts.technical_eligible || 0}</p>
      <p class="text-xs text-slate-500">Technical Ready</p>
    </div>
    <div class="card-executive p-4 text-center">
      <p class="text-2xl font-bold text-cyan-400">{stageCounts.technical_passed || 0}</p>
      <p class="text-xs text-slate-500">Technical Passed</p>
    </div>
    <div class="card-executive p-4 text-center">
      <p class="text-2xl font-bold text-pink-400">{stageCounts.hr_eligible || 0}</p>
      <p class="text-xs text-slate-500">HR Ready</p>
    </div>
    <div class="card-executive p-4 text-center">
      <p class="text-2xl font-bold text-success">{stageCounts.hr_passed || 0}</p>
      <p class="text-xs text-slate-500">Final Selected</p>
    </div>
  </div>

  <!-- Action Cards -->
  <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
    <!-- AI Resume Screening -->
    <div class="card-executive p-6">
      <div class="flex items-center gap-3 mb-4">
        <div class="p-2 rounded-lg bg-info/10">
          <Brain class="w-5 h-5 text-info" />
        </div>
        <div>
          <h3 class="font-semibold text-slate-200">AI Resume Screening</h3>
          <p class="text-sm text-slate-500">{stageCounts.applied || 0} candidates pending</p>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <Input 
          type="number" 
          bind:value={topN} 
          min="1" 
          max="100"
          class="w-20 bg-obsidian-850 border-slate-700"
        />
        <Button 
          onclick={handleSelectTopResumes}
          disabled={$selectTopMutation.isPending || (stageCounts.applied || 0) === 0}
          class="flex-1 bg-info hover:bg-info/90"
        >
          Select Top {topN}
        </Button>
      </div>
    </div>

    <!-- Aptitude Test -->
    <div class="card-executive p-6">
      <div class="flex items-center gap-3 mb-4">
        <div class="p-2 rounded-lg bg-purple-500/10">
          <FileText class="w-5 h-5 text-purple-400" />
        </div>
        <div>
          <h3 class="font-semibold text-slate-200">Aptitude Test</h3>
          <p class="text-sm text-slate-500">{stageCounts.aptitude_eligible || 0} ready to take test</p>
        </div>
      </div>
      <Button variant="outline" href="/jobs/{jobId}/aptitude" class="w-full">
        Configure Test
      </Button>
    </div>

    <!-- Technical Interviews -->
    <div class="card-executive p-6">
      <div class="flex items-center gap-3 mb-4">
        <div class="p-2 rounded-lg bg-amber-500/10">
          <Video class="w-5 h-5 text-amber-400" />
        </div>
        <div>
          <h3 class="font-semibold text-slate-200">Technical Interviews</h3>
          <p class="text-sm text-slate-500">{stageCounts.technical_eligible || 0} ready for interview</p>
        </div>
      </div>
      <Button variant="outline" href="/jobs/{jobId}/technical" class="w-full">
        View Interviews
      </Button>
    </div>
  </div>

  <!-- Candidates Table -->
  <Tabs.Root value="all">
    <Tabs.List class="bg-obsidian-900 border border-slate-800">
      <Tabs.Trigger value="all">All Candidates</Tabs.Trigger>
      <Tabs.Trigger value="pipeline">Pipeline View</Tabs.Trigger>
    </Tabs.List>
    
    <Tabs.Content value="all" class="mt-4">
      <CandidateTable 
        candidates={$candidatesQuery.data?.data || []} 
        isLoading={$candidatesQuery.isLoading} 
      />
    </Tabs.Content>
    
    <Tabs.Content value="pipeline" class="mt-4">
      <PipelineView 
        candidates={$candidatesQuery.data?.data || []} 
        jobId={jobId}
      />
    </Tabs.Content>
  </Tabs.Root>
</div>
```

---

## 13. ERROR HANDLING & UX

```typescript
// src/lib/utils/permissions.ts
export async function checkMediaPermissions(): Promise<'granted' | 'denied' | 'prompt'> {
  try {
    const camera = await navigator.permissions.query({ name: 'camera' as PermissionName });
    const mic = await navigator.permissions.query({ name: 'microphone' as PermissionName });
    
    if (camera.state === 'denied' || mic.state === 'denied') return 'denied';
    if (camera.state === 'granted' && mic.state === 'granted') return 'granted';
    return 'prompt';
  } catch {
    return 'prompt';
  }
}

// Toast patterns (use throughout)
import { toast } from 'svelte-sonner';

// Success
toast.success('Interview started', { description: 'Good luck!' });

// Error with retry
toast.error('Connection lost', {
  description: 'WebSocket disconnected',
  action: { label: 'Retry', onClick: () => reconnect() },
});

// Loading promise
toast.promise(submitInterview(), {
  loading: 'Submitting interview...',
  success: 'Interview submitted for evaluation',
  error: 'Failed to submit',
});
```

---

## 14. IMPLEMENTATION CHECKLIST

```
PHASE 1: FOUNDATION
[  ] Initialize SvelteKit + Tailwind + shadcn-svelte
[  ] Generate API types from swagger/new-swagger.yaml
[  ] Set up TanStack Query with global error handling
[  ] Create auth store with localStorage persistence

PHASE 2: AUTHENTICATION & COMPANY SETUP
[  ] Build company registration page (/register)
[  ] Build login page (/login)
[  ] Implement auth guards for dashboard routes
[  ] Create company profile page

PHASE 3: JOB REQUIREMENTS
[  ] Build job creation form with skills input
[  ] Build job list page with status filters
[  ] Build job detail page with candidate pipeline
[  ] Implement job edit functionality

PHASE 4: CANDIDATE MANAGEMENT
[  ] Build candidate application form (public route)
[  ] Build candidate table with filtering/sorting
[  ] Build candidate detail page with interview history
[  ] Implement AI resume screening action
[  ] Implement select top candidates actions

PHASE 5: INTERVIEW SYSTEM
[  ] Implement media store with permission handling
[  ] Build VideoPreview component
[  ] Build AudioVisualizer component
[  ] Implement WebSocket interview store
[  ] Build TranscriptPanel with streaming
[  ] Build glassmorphic ControlBar
[  ] Build interview detail view with scores

PHASE 6: DASHBOARD & ANALYTICS
[  ] Build dashboard overview with stats
[  ] Build jobs overview component
[  ] Build recent candidates component
[  ] Add analytics charts (optional)

PHASE 7: POLISH
[  ] Add skeleton loaders everywhere
[  ] Add svelte-sonner notifications
[  ] Ensure responsive mobile layouts
[  ] Test complete flow end-to-end
```

---

## 15. COMPLETE USER JOURNEY SUMMARY

```
1. COMPANY REGISTERS
   → POST /company/register
   → Store workspace_id, user_id, company_id
   → Redirect to Dashboard

2. COMPANY CREATES JOB
   → POST /job-requirements/company/{company_id}
   → Job appears on Dashboard

3. CANDIDATES APPLY (External)
   → GET /candidates/{job_id}/apply-form
   → POST /candidates/apply
   → Candidates appear under job

4. HR SCREENS RESUMES
   → Dashboard shows candidates count
   → Click "Select Top N" → POST /candidates/{job_id}/select-top-resumes
   → AI ranks candidates, generates passwords
   → Selected move to "aptitude_eligible"

5. CANDIDATES TAKE APTITUDE
   → HR configures test: POST /aptitude/create
   → Candidates login, take test, submit
   → HR selects top: POST /aptitude/select-top-candidates
   → Passed move to "technical_eligible"

6. TECHNICAL INTERVIEWS
   → HR sees eligible candidates
   → Candidate starts: POST /technical-interview/start/{candidate_id}
   → WebSocket interview happens
   → System completes: POST /technical-interview/complete/{id}
   → HR selects top: POST /technical-interview/select-top-candidates

7. HR INTERVIEWS
   → Same flow as technical
   → POST /hr-interview/start/{candidate_id}
   → POST /hr-interview/complete/{id}
   → POST /hr-interview/select-top-candidates
   → Final candidates marked for hiring

8. DASHBOARD SHOWS EVERYTHING
   → Stats: Total jobs, candidates, interviews
   → Per-job: Pipeline stages, scores, recommendations
   → Analytics: Hiring velocity, score distributions
```

**END OF MASTER INSTRUCTION SET**
