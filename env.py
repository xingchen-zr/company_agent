#存放各种可能随时可修改的变量
from langchain_deepseek.chat_models import ChatDeepSeek

text_Path = r"D:\company_agent\Document_Processing\金融公司制度与操作手册.txt"
encoding = "utf-8"
chunk_size = 500
chunk_overlap = 100
vector_path = r"D:\company_agent\Chroma_db"
k_top:int = 10
MODEL = ChatDeepSeek(model="deepseek-v4-pro")
Expired_Time = 60*60*48
system_prompt = ("你是一位充分了解公司制度的助手,"
                "专门解答公司内员工的各种对公司相关事务的疑惑,"
                "当你回答与公司制度,福利,规则相关的问题时,必须调用工具查询,"
                "你的回答必须有理有据,回答时要附带你回答问题的依据,"
                "没有依据的问题你要回答不知道")
relevance_threshold = 0.3
COOKIE_NAME = "chat_session_id"
COOKIE_MAX_AGE = 60 * 60 * 48