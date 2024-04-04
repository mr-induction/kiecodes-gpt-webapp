import asyncio
from typing import List, Optional

import aiohttp
from fastapi import FastAPI, Request
from openai import AsyncOpenAI
from openai.types.beta.threads.run import RequiredAction, LastError
from openai.types.beta.threads.run_submit_tool_outputs_params import ToolOutput
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI()

origins = [
    "https://kiecodes-gpt-webapp.vercel.app",
    "https://main--esotericagrimoire.netlify.app",
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://localhost:3003",
    "http://localhost:3004",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = AsyncOpenAI(
    api_key="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",
)
assistant_id = "asst_cW9s3A0A2o1ws3mi8XwClXwJ"
run_finished_states = ["completed", "failed", "cancelled", "expired", "requires_action"]

class RunStatus(BaseModel):
    run_id: str
    thread_id: str
    status: str
    required_action: Optional[RequiredAction]
    last_error: Optional[LastError]

class ThreadMessage(BaseModel):
    content: str
    role: str
    hidden: bool
    id: str
    created_at: int

class Thread(BaseModel):
    messages: List[ThreadMessage]

class CreateMessage(BaseModel):
    content: str

class Goal(BaseModel):
    goal: str

@app.options("/{rest_of_path:path}")
async def preflight_handler(request: Request, rest_of_path: str) -> JSONResponse:
    response = JSONResponse(content={"message": "Preflight request successful"})
    response.headers["Access-Control-Allow-Origin"] = request.headers.get("Origin", "*")
    response.headers["Access-Control-Allow-Methods"] = "POST, GET, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response

@app.post("/api/decompose-goal")
async def decompose_goal(goal: Goal):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer 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",
            },
            json={
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "You are an AI assistant that decomposes goals into actionable milestones."},
                    {"role": "user", "content": f"Decompose the following goal into actionable milestones in a bullet point format: {goal.goal}"}
                ]
            }
        ) as response:
            result = await response.json()
            brainstormed_milestones = result["choices"][0]["message"]["content"].split("\n")

    # Create a new thread for recommending a demon based on the decomposed goal
    demon_thread = await client.beta.threads.create()

    # Combine the brainstormed milestones into a single string
    milestones_str = "\n".join(brainstormed_milestones)

    await client.beta.threads.messages.create(
        thread_id=demon_thread.id,
        content=f"Based on the following decomposed goal:\n{milestones_str}\n\nRecommend a demon to help achieve this goal. Use your Retrieval tool to access the information in revisedintro-2.pdf. Provide the demon's name and explain why this demon is helpful for achieving this particular goal.",
        role="user",
    )

    demon_response = await client.beta.threads.runs.create(
        thread_id=demon_thread.id,
        assistant_id=assistant_id,
    )

    while demon_response.status not in run_finished_states:
        await asyncio.sleep(1)
        demon_response = await client.beta.threads.runs.retrieve(
            thread_id=demon_thread.id,
            run_id=demon_response.id,
        )

    demon_messages = await client.beta.threads.messages.list(thread_id=demon_thread.id)
    demon_recommendation = ""
    for message in demon_messages.data:
        if message.role == "assistant":
            demon_recommendation = message.content[0].text.value
            break

    return {"milestones": brainstormed_milestones, "demon_recommendation": demon_recommendation}

@app.post("/api/new")
async def post_new():
    thread = await client.beta.threads.create()
    await client.beta.threads.messages.create(
        thread_id=thread.id,
        content="Greet the user and tell it about yourself and ask it what it is looking for.",
        role="user",
        metadata={
            "type": "hidden"
        }
    )
    run = await client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id
    )

    return RunStatus(
        run_id=run.id,
        thread_id=thread.id,
        status=run.status,
        required_action=run.required_action,
        last_error=run.last_error
    )

@app.get("/api/threads/{thread_id}/runs/{run_id}")
async def get_run(thread_id: str, run_id: str):
    run = await client.beta.threads.runs.retrieve(
        thread_id=thread_id,
        run_id=run_id
    )

    return RunStatus(
        run_id=run.id,
        thread_id=thread_id,
        status=run.status,
        required_action=run.required_action,
        last_error=run.last_error
    )

@app.post("/api/threads/{thread_id}/runs/{run_id}/tool")
async def post_tool(thread_id: str, run_id: str, tool_outputs: List[ToolOutput]):
    run = await client.beta.threads.runs.submit_tool_outputs(
        run_id=run_id,
        thread_id=thread_id,
        tool_outputs=tool_outputs
    )
    return RunStatus(
        run_id=run.id,
        thread_id=thread_id,
        status=run.status,
        required_action=run.required_action,
        last_error=run.last_error
    )

@app.get("/api/threads/{thread_id}")
async def get_thread(thread_id: str):
    messages = await client.beta.threads.messages.list(
        thread_id=thread_id
    )

    result = [
        ThreadMessage(
            content=message.content[0].text.value,
            role=message.role,
            hidden="type" in message.metadata and message.metadata["type"] == "hidden",
            id=message.id,
            created_at=message.created_at
        )
        for message in messages.data
    ]

    return Thread(
        messages=result,
    )

@app.post("/api/threads/{thread_id}")
async def post_thread(thread_id: str, message: CreateMessage):
    await client.beta.threads.messages.create(
        thread_id=thread_id,
        content=message.content,
        role="user"
    )

    run = await client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id
    )

    return RunStatus(
        run_id=run.id,
        thread_id=thread_id,  # Use thread_id instead of thread.id
        status=run.status,
        required_action=run.required_action,
        last_error=run.last_error
    )
