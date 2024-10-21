from openai import OpenAI
import os

conversation_history = {}
MAX_CONVERSATION_ROUND = 10
MAX_CONVERSATION_HISTORY_SIZE = 2 * MAX_CONVERSATION_ROUND


client = OpenAI(
    api_key=os.environ.get("ZHIPU_API_KEY"),
    base_url="https://open.bigmodel.cn/api/paas/v4/",
)


def llm_reply(user_id, message, image_description):
    system_prompt = """请你作为一个小学数学老师，擅长教育学生数学思维，帮助引导一步步解答数学题。过程中可以引导学生列出方程式，但是不要告诉答案。每次启发式提问不要超过2个，每次回答保持35字以内。如果作业描述不完整，引导学生说一下描述一下题目并说一下对题目的理解。
## 作业描述如下：
{homework_description}
"""
    global conversation_history
    
    initial_message = {
        "role": "system", 
        "content": system_prompt.format(homework_description=image_description)
    }

    user_conversation_history = conversation_history.get(user_id, [])
    print(f"user_conversation_history: {user_conversation_history}")
    user_conversation_history = user_conversation_history[-MAX_CONVERSATION_HISTORY_SIZE:]
    user_conversation_history.append({"role": "user", "content": message})
    conversation_history[user_id] = user_conversation_history
    
    response = client.chat.completions.create(
        model="GLM-4-AirX",
        # model="gpt-4o",
        messages=[initial_message] + user_conversation_history,
        stream=True
    )
    
    partial_message = ""
    for chunk in response:
        if chunk.choices[0].delta.content:
            partial_message += chunk.choices[0].delta.content
            yield chunk.choices[0].delta.content
    
    user_conversation_history.append({"role": "assistant", "content": partial_message})
    conversation_history[user_id] = user_conversation_history