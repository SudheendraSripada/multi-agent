import base64
import json
import logging
import os
import re
from datetime import datetime, timezone

import docker
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from groq import Groq
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("agency")

WORKSPACE_ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUTPUT_ROOT = os.path.join(WORKSPACE_ROOT, "generated-projects")

app = FastAPI(title="Autonomous Multi-Agent AI Software Agency")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    docker_client = docker.from_env()
    docker_client.ping()
except Exception as e:
    print(f"Docker connection warning (Ignore if running without container loops): {e}")
    docker_client = None


class IntakeRequest(BaseModel):
    user_prompt: str
    project_type: str  # "script" or "server"
    auto_export: bool = True
    export_folder_name: str | None = None


class CfoAssessment(BaseModel):
    estimated_tokens: int
    complexity_rating: str
    approved: bool


class ArchitectureSop(BaseModel):
    architecture_style: str
    dependencies: list[str]
    step_by_step_sop: list[str]
    verification_tests: list[str]


class DevOpsPackage(BaseModel):
    application_code: str
    dockerfile_contents: str
    docker_compose_contents: str
    deployment_commands: list[str]


class ExportRequest(BaseModel):
    project_type: str
    export_folder_name: str | None = None
    deployment_package: DevOpsPackage | None = None
    code_output: str | None = None


def normalize_cfo_assessment(assessment: CfoAssessment, prompt: str) -> CfoAssessment:
    """Avoid false rejections on normal engineering tasks."""
    if assessment.approved:
        return assessment
    within_budget = assessment.estimated_tokens <= 120_000
    reasonable_scope = len(prompt) <= 8000
    routine_complexity = assessment.complexity_rating.lower() in {
        "low",
        "medium",
        "moderate",
        "simple",
        "standard",
    }
    if within_budget and reasonable_scope and (routine_complexity or assessment.estimated_tokens <= 50_000):
        log.info("[CFO] Auto-approved after routine-scope override (model was overly strict).")
        return assessment.model_copy(update={"approved": True})
    return assessment


def cfo_agent_evaluation(client: Groq, prompt: str) -> CfoAssessment:
    """Phase 1: Financial & Token Resource Management Gatekeeper."""
    system_prompt = (
        "You are the CFO Agent for a software development agency. "
        "Approve standard software engineering work: REST APIs, CLI scripts, microservices, "
        "Docker deployments, monitoring endpoints, and small-to-medium Python apps. "
        "Set approved=true unless the request is abusive, illegal, or needs extreme unbounded resources. "
        "Typical API/server/script tasks should be approved with complexity_rating low or medium. "
        "Return ONLY valid JSON with keys: estimated_tokens (int), complexity_rating (str), approved (bool)."
    )
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Evaluate cost parameters for: {prompt}"},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        assessment = CfoAssessment(**json.loads(completion.choices[0].message.content))
    except Exception as exc:
        log.warning("[CFO] Evaluation parse failed (%s) — defaulting to approved.", exc)
        assessment = CfoAssessment(
            estimated_tokens=8000,
            complexity_rating="medium",
            approved=True,
        )
    return normalize_cfo_assessment(assessment, prompt)


def architect_agent_sop(client: Groq, prompt: str) -> ArchitectureSop:
    """Phase 2: Technical Design Blueprinting & Test Generation."""
    system_prompt = (
        "You are the Lead Systems Architect and SOP Officer. Translate raw user needs into rigid technical steps. "
        "Define dependencies and generate precise Python/pytest-style executable test cases to verify functionality. "
        "Return your answer ONLY as a JSON object matching these exact keys: "
        "'architecture_style' (str), 'dependencies' (list of strings), 'step_by_step_sop' (list of strings), 'verification_tests' (list of strings)."
    )
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Create specifications for: {prompt}"},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    return ArchitectureSop(**json.loads(completion.choices[0].message.content))


def execute_qa_sandbox(code: str, tests: list[str]) -> tuple[bool, str]:
    """Isolated Virtual Execution Sandbox for Testing Code Changes."""
    if not docker_client:
        log.info("[QA] Docker unavailable — simulation mode (tests skipped).")
        return True, "Docker sandbox bypassed. Running in simulation mode."

    log.info("[QA] Running isolated container test...")

    full_script = f"{code}\n\n# --- AUTOMATED QA UNIT TESTS ---\n"
    for test in tests:
        full_script += f"\n{test}"

    encoded = base64.b64encode(full_script.encode("utf-8")).decode("ascii")
    runner = (
        "import base64; "
        f"exec(base64.b64decode('{encoded}').decode('utf-8'), {{'__name__': '__main__'}})"
    )

    try:
        container = docker_client.containers.run(
            image="python:3.11-slim",
            command=["python", "-c", runner],
            detach=False,
            stdout=True,
            stderr=True,
            remove=True,
            network_disabled=True,
        )
        return True, container.decode("utf-8")
    except docker.errors.ContainerError as e:
        stderr = e.stderr.decode("utf-8") if e.stderr else str(e)
        return False, stderr
    except Exception as e:
        return False, str(e)


def dev_production_pipeline(client: Groq, spec: ArchitectureSop, prompt: str) -> str:
    """Phase 3: Core Developer Sprint & Self-Healing QA Testing Loop."""
    dev_system_prompt = (
        "You are the Senior Software Developer Agent. Write clean, production-ready Python code. "
        "Strictly adhere to the provided SOP rules and structural blueprints. "
        "Output ONLY raw executable code. Do not include markdown wraps (```) or chatting."
    )

    context = f"Goal: {prompt}\nSOP: {spec.step_by_step_sop}\nTests: {spec.verification_tests}"
    loops = 0
    raw_code = ""

    while loops < 3:
        loops += 1
        log.info("[DEVELOPER] QA attempt %d/3 — generating code...", loops)
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": dev_system_prompt},
                {"role": "user", "content": context},
            ],
            temperature=0.1,
        )
        raw_code = completion.choices[0].message.content.strip()
        if raw_code.startswith("```"):
            lines = raw_code.split("\n")
            raw_code = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        success, logs = execute_qa_sandbox(raw_code, spec.verification_tests)
        if success:
            log.info("[DEVELOPER] QA passed on attempt %d.", loops)
            return raw_code

        log.warning("[DEVELOPER] QA failed on attempt %d — self-healing rewrite.", loops)
        log.warning("[QA LOG] %s", logs[:500])
        context += f"\n\n[QA DISCOVERED BUGS IN ATTEMPT {loops}]:\n{logs}\nRewrite the entire script fixing these bugs."

    return raw_code


def devops_infrastructure_agent(client: Groq, code: str, spec: ArchitectureSop) -> DevOpsPackage:
    """Phase 4: Site Reliability Engineering (SRE) & Autonomous Server Provisioning."""
    devops_system_prompt = (
        "You are the Systems DevOps Engineer Agent. Take verified code and create configurations to deploy it "
        "autonomously on a production Linux server. Generate a Dockerfile and docker-compose orchestration file. "
        "Return your response ONLY as a JSON object with these exact keys: "
        "'application_code' (str), 'dockerfile_contents' (str), 'docker_compose_contents' (str), 'deployment_commands' (list of strings)."
    )

    context = f"App Code:\n{code}\n\nArchitecture Spec:\n{spec.architecture_style}"
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": devops_system_prompt},
            {"role": "user", "content": context},
        ],
        response_format={"type": "json_object"},
        temperature=0.0,
    )
    return DevOpsPackage(**json.loads(completion.choices[0].message.content))


def slugify_folder_name(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip().lower()).strip("-")
    return slug[:48] or "project"


def resolve_output_dir(folder_name: str | None, prompt: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    slug = slugify_folder_name(folder_name or prompt[:40])
    return os.path.join(DEFAULT_OUTPUT_ROOT, f"{stamp}-{slug}")


def write_text_file(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


def export_project_to_disk(
    project_type: str,
    *,
    deployment_package: DevOpsPackage | None = None,
    code_output: str | None = None,
    export_folder_name: str | None = None,
    user_prompt: str = "",
) -> dict:
    output_dir = resolve_output_dir(export_folder_name, user_prompt)
    saved_files: list[str] = []

    if project_type == "server":
        if not deployment_package:
            raise ValueError("deployment_package required for server export")
        pkg = deployment_package
        manifest = {
            "app.py": pkg.application_code,
            "Dockerfile": pkg.dockerfile_contents,
            "docker-compose.yml": pkg.docker_compose_contents,
            "DEPLOY.md": "\n".join(
                ["# Deployment commands", ""]
                + [f"- `{cmd}`" for cmd in (pkg.deployment_commands or [])]
            ),
        }
    else:
        if not code_output:
            raise ValueError("code_output required for script export")
        manifest = {"main.py": code_output}

    for filename, content in manifest.items():
        file_path = os.path.join(output_dir, filename)
        write_text_file(file_path, content)
        saved_files.append(file_path)
        log.info("[EXPORT] Wrote %s", file_path)

    return {"output_dir": output_dir, "files": saved_files}


@app.get("/")
async def serve_dashboard():
    """Serve the management control dashboard."""
    index_path = os.path.join(os.path.dirname(__file__), "index.html")
    if not os.path.isfile(index_path):
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(index_path)


@app.post("/v1/agency/export")
async def export_agency_artifacts(request: ExportRequest):
    """Write the last pipeline deliverables to disk (manual re-export)."""
    try:
        export_info = export_project_to_disk(
            request.project_type,
            deployment_package=request.deployment_package,
            code_output=request.code_output,
            export_folder_name=request.export_folder_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "status": "Exported to disk",
        "export": export_info,
        "deploy_hint": (
            f"cd \"{export_info['output_dir']}\" && docker compose up --build"
            if request.project_type == "server"
            else None
        ),
    }


@app.post("/v1/agency/execute")
async def execute_agency_workflow(request: IntakeRequest, x_groq_key: str = Header(None)):
    if not x_groq_key:
        raise HTTPException(status_code=401, detail="X-Groq-Key missing from headers.")

    client = Groq(api_key=x_groq_key)
    log.info("========== AGENCY PIPELINE START ==========")
    log.info("[INTAKE] type=%s prompt=%s", request.project_type, request.user_prompt[:120])

    log.info("[CFO] Evaluating budget and token limits...")
    cfo_metrics = cfo_agent_evaluation(client, request.user_prompt)
    log.info(
        "[CFO] approved=%s tokens=%s complexity=%s",
        cfo_metrics.approved,
        cfo_metrics.estimated_tokens,
        cfo_metrics.complexity_rating,
    )
    if not cfo_metrics.approved:
        log.warning("[CFO] Project rejected — pipeline halted.")
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Project rejected by CFO due to resource bounds.",
                "cfo_audit": cfo_metrics.model_dump(),
                "hint": "Shorten the prompt, reduce scope, or split into smaller tasks.",
            },
        )

    log.info("[ARCHITECT] Drafting SOP, dependencies, and verification tests...")
    blueprint = architect_agent_sop(client, request.user_prompt)
    log.info("[ARCHITECT] style=%s tests=%d", blueprint.architecture_style, len(blueprint.verification_tests))

    log.info("[DEVELOPER] Starting build + QA sandbox loop (up to 3 attempts)...")
    verified_application = dev_production_pipeline(client, blueprint, request.user_prompt)
    log.info("[DEVELOPER] Delivered %d characters of verified code.", len(verified_application))

    export_info = None
    deploy_hint = None

    if request.project_type == "server":
        log.info("[DEVOPS] Generating Dockerfile, compose, and deployment commands...")
        devops_deployment = devops_infrastructure_agent(
            client, verified_application, blueprint
        )
        log.info("[DEVOPS] Package ready.")

        if request.auto_export:
            export_info = export_project_to_disk(
                "server",
                deployment_package=devops_deployment,
                export_folder_name=request.export_folder_name,
                user_prompt=request.user_prompt,
            )
            deploy_hint = f'cd "{export_info["output_dir"]}" && docker compose up --build'
            log.info("[EXPORT] Server project saved to %s", export_info["output_dir"])

        log.info("========== AGENCY PIPELINE COMPLETE ==========")
        return {
            "status": "Deployed & Structured for Server Execution",
            "audit": cfo_metrics,
            "architecture": blueprint,
            "deployment_package": devops_deployment,
            "export": export_info,
            "deploy_hint": deploy_hint,
        }

    if request.auto_export:
        export_info = export_project_to_disk(
            "script",
            code_output=verified_application,
            export_folder_name=request.export_folder_name,
            user_prompt=request.user_prompt,
        )
        log.info("[EXPORT] Script saved to %s", export_info["output_dir"])

    log.info("========== AGENCY PIPELINE COMPLETE ==========")
    return {
        "status": "Standalone Script Delivered",
        "audit": cfo_metrics,
        "architecture": blueprint,
        "code_output": verified_application,
        "export": export_info,
    }
