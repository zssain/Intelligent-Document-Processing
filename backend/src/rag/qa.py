from openai import OpenAI
from config.settings import settings
from typing import List, Dict
from sqlalchemy.orm import Session
import logging
import json

logger = logging.getLogger(__name__)

class QualityAssurance:
    """Handles grounded question answering using LLMs."""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_chat_model
        
    def answer_question(self, question: str, context_chunks: List[dict], language: str = 'english') -> dict:
        """Answers a question based ONLY on provided context.
        
        Args:
            question: User's question
            context_chunks: List of retrieved chunks with metadata
            language: The language the response should be in ('english' or 'arabic')
            
        Returns:
            dict: { 'answer': '...', 'sources': [...] }
        """
        if not context_chunks:
            return {
                "answer": "I can only help with the uploaded documents. Please upload a document first or ask a question about an existing one.",
                "sources": []
            }
            
        # Prepare context prompt
        context_str = "\n\n".join([f"Source: {c['metadata'].get('statement', 'Document')} (Similarity: {c['score']:.2f})\nContent: {c['text']}" for c in context_chunks])
        
        if language == 'arabic':
            system_prompt = (
                "أنت مساعد ذكي محترف لتحليل المستندات. مهمتك هي تقديم تحليل دقيق ومبني على السياق المقدم.\n\n"
                "### متطلب اللغة (حرج):\n"
                "- يجب أن يكون ردك بالكامل باللغة العربية.\n"
                "- جميع التحليلات، وعناوين الجداول، والملخصات يجب أن تكون باللغة العربية.\n\n"
                "### قواعد التفاعل:\n"
                "1. **التحيات**: إذا قام المستخدم بتحيتك، رد بأدب وعرف نفسك كمساعد لتحليل المستندات.\n"
                "2. **النطاق**: إذا كان السؤال خارج نطاق المستندات المقدمة، رد بـ: 'يمكنني المساعدة فقط في المستندات التي تم تحميلها'.\n"
                "3. **التنسيق**: استخدم Markdown. للملخصات، قدم: 1) فقرة 'نظرة عامة'، 2) جدول 'البيانات الرئيسية'، 3) 'أهم الملاحظات' كقائمة نقطية.\n"
                "4. **الأرقام**: استخدم **النص العريض** للأرقام (مثال: **1.2 مليون دولار**).\n"
                "5. **النغمة**: حافظ على نبرة مهنية وموجزة."
            )
        else:
            system_prompt = (
                f"You are a professional document analysis assistant. Your task is to provide accurate, grounded analysis based on the provided context.\n\n"
                f"### LANGUAGE REQUIREMENT (CRITICAL):\n"
                f"- You MUST respond entirely in {language.upper()}.\n"
                f"- All analysis, table headers, and summaries must be in {language.upper()}.\n\n"
                "### Interaction Rules:\n"
                "1. **Greetings**: If the user greets you (e.g., 'Hello', 'Hi'), respond politely and introduce yourself as a document analysis assistant. Do NOT require context for basic greetings.\n"
                "2. **Leniency & Scope**: \n"
                "   - Be lenient with language variation; understand the user's intent even if they use different terms than those in the documents.\n"
                "   - If the user asks a question that cannot be answered using the provided documents, or if the question is out of scope, respectfully tell them: 'I can only help with the uploaded documents. Please ask a question about an existing document.'.\n"
                "3. **Groundedness**: For factual questions, answer using the provided context. If the information is missing or the question is out of scope, use the respectful message above.\n"
                "4. **Structure**: Use Markdown for readability:\n"
                "   - **Summary Requests**: If asked for a summary, always provide: 1) A brief 'Overview' paragraph, 2) A 'Key Data' **Markdown table** (if applicable), and 3) 'Key Observations' as bullet points.\n"
                "   - Use **bold text** for key figures (e.g., **$1.2M**, **15% growth**).\n"
                "   - Use **Markdown tables** when presenting multiple data points.\n"
                "5. **Tone**: Maintain a professional, concise, and helpful tone."
            )
        
        user_prompt = f"### Question:\n{question}\n\n### Context:\n{context_str}\n\n### Response Language:\n{language.upper()}"
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0 # High precision, no randomness
            )
            
            answer = response.choices[0].message.content
            
            # Extract unique sources
            sources = list(set([f"{c['metadata'].get('statement', 'Document')}" for c in context_chunks if c['score'] > 0.4]))
            
            return {
                "answer": answer,
                "sources": sources
            }
            
        except Exception as e:
            logger.error(f"QA Failed: {e}")
            raise

    def stream_answer(self, question: str, db: Session, language: str = 'english', entity: str = None, document_type: str = None, document_ids: List[str] = None):
        """Streams an answer based on provided context.
        
        Yields:
            str: JSON chunks containing either text or metadata (sources)
        """
        logger.info(f"Starting stream_answer for question: '{question}' with document_ids: {document_ids}")
        from src.rag.retriever import Retriever
        
        # 1. Retrieve Context
        retriever = Retriever(db)
        context_chunks = retriever.get_relevant_context(
            question,
            entity=entity,
            document_type=document_type,
            document_ids=document_ids,
            limit=10 # Increased for deeper analysis
        )

        if not context_chunks and not retriever._is_greeting(question):
            error_msg = "I can only help with the uploaded documents. Please upload a document first or ask a question about an existing one."
            if language == 'arabic':
                error_msg = "يمكنني المساعدة فقط في المستندات التي تم تحميلها. يرجى تحميل مستند أولاً أو طرح سؤال حول مستند موجود."
            yield json.dumps({"content": error_msg}) + "\n"
            yield json.dumps({"sources": []}) + "\n"
            return
            
        context_str = "\n\n".join([f"Source: {c['metadata'].get('statement', 'Document')}\nContent: {c['text']}" for c in context_chunks])
        
        if language == 'arabic':
            system_prompt = (
                "أنت مساعد ذكي محترف وخبير في تحليل المستندات. مهمتك هي تقديم تحليل دقيق وعميق ومبني بالكامل على المستندات المقدمة.\n\n"
                "### قيود الاستجابة (حمايه من الهلوسة):\n"
                "1. **التزام بالسياق**: أجب فقط بناءً على المعلومات المتوفرة في المستندات. إذا لم تكن المعلومة موجودة، قل بوضوح: 'يمكنني المساعدة فقط في المستندات التي تم تحميلها'.\n"
                "2. **الأسئلة العامة**: إذا سأل المستخدم أسئلة عامة أو غير متعلقة بالمستندات (مثل 'كيف حالك؟' أو 'ما هو الطقس؟')، رد بأدب بأنك مختص في تحليل المستندات فقط.\n"
                "3. **لا للتخمين**: لا تقم بإنشاء حقائق أو أرقام من عندك.\n\n"
                "### متطلب اللغة (حرج):\n"
                "- يجب أن يكون ردك بالكامل باللغة العربية.\n"
                "- جميع التحليلات، وعناوين الجداول، والملخصات يجب أن تكون باللغة العربية.\n\n"
                "### قواعد التفاعل:\n"
                "1. **التحيات**: رد بأدب وعرّف نفسك كمساعد ذكاء اصطناعي لتحليل المستندات.\n"
                "2. **النطاق والدقة**: إذا كان السؤال يتطلب معلومات غير موجودة في السياق، قل بوضوح: 'يمكنني المساعدة فقط في المستندات التي تم تحميلها'.\n"
                "3. **التنسيق**: استخدم Markdown بشكل مكثف (جداول للبيانات، قوائم للملاحظات). استخدم **النص العريض** لكل الأرقام والنسب المئوية."
            )
        else:
            system_prompt = (
                f"You are a professional senior document analysis assistant. Your goal is to provide deep, accurate, and grounded analysis based strictly on the provided context.\n\n"
                f"### HALLUCINATION PREVENTION (STRICT):\n"
                f"1. **Grounded Only**: Do NOT answer using outside knowledge. If the answer is not in the context, state: 'I can only help with the uploaded documents. Please ask a question about an existing document.'.\n"
                f"2. **Casual Queries**: If the user asks casual, personal, or general knowledge questions (e.g., 'What is the capital of France?', 'Tell me a joke'), politely respond that you are a specialized document analysis assistant.\n"
                f"3. **No Guessing**: Never fabricate numbers, dates, or facts.\n\n"
                f"### LANGUAGE REQUIREMENT (CRITICAL):\n"
                f"- You MUST respond entirely in {language.upper()}.\n\n"
                "### Interaction Rules:\n"
                "1. **Analysis Style**: Be analytical. Explain trends and significant information.\n"
                "2. **Formatting**: \n"
                "   - Use **Markdown tables** for structured data.\n"
                "   - Use **bold text** for all numbers and key values.\n"
                "3. **Tone**: Maintain a high-end, professional, and objective consulting tone."
            )       
        user_prompt = f"### Question:\n{question}\n\n### Context:\n{context_str}\n\n### Response Language:\n{language.upper()}"
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,
                stream=True
            )
            
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield json.dumps({"content": chunk.choices[0].delta.content}) + "\n"
            
            # Final metadata chunk
            if context_chunks:
                sources = list(set([f"{c['metadata'].get('statement', 'Document')}" for c in context_chunks if c['score'] > 0.4]))
                yield json.dumps({"sources": sources}) + "\n"
            
        except Exception as e:
            logger.error(f"Streaming QA Failed: {e}")
            yield json.dumps({"error": str(e)}) + "\n"
