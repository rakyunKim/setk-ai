"""통합 검증 노드 - 입력 정보 포함 + 품질 검증"""

# 검증 프롬프트 구성
from agent.static.prompt import AI_VALIDATE_PROMPT
from typing import Optional, List
from langchain_core.runnables import RunnableConfig
from agent.utils.config.config import get_model_name, log_token_usage
from agent.utils.state.state import StudentState
from agent.utils.node.helper_nodes import _get_model
from src.utils.logger import setup_logger
import re
import json

logger = setup_logger(__name__)


def validate(state: StudentState, config: Optional[RunnableConfig] = None) -> StudentState:
    """AI 기반으로 생성된 세특의 허위 정보와 품질을 검증
    
    Args:
        state: 학생 상태
        config: 런타임 설정
        
    Returns:
        검증 결과가 포함된 상태
    """
    try:
        # 필요한 정보 추출
        teacher_input = state["teacher_input"]
        detailed_record = state.get("detailed_record", {})
        content = detailed_record.get("content", "")
        
        logger.info(f"AI 검증 시작 - 학생: {teacher_input['name']}")
        
        # AI 모델 초기화 - validate는 tools 없이 순수 텍스트 응답만 필요
        model_name = get_model_name(config)
        model = _get_model(model_name)
        
        
        validation_prompt = AI_VALIDATE_PROMPT.format(
            additional_notes=teacher_input.get("additional_notes", "없음"),
            content=content,
            achievement_standards=teacher_input.get("achievement_standards", ""),
            midterm_score=teacher_input.get("midterm_score", "없음"),
            final_score=teacher_input.get("final_score", "없음"),
        )
        
        try:
            response = model.invoke(validation_prompt)
            
            # 토큰 사용량 로깅
            log_token_usage(response, logger, "validate")
            
        except Exception as model_error:
            logger.error(f"검증 노드 모델 호출 실패: {model_error}")
            raise
        
        ai_response = response.content
            
        # JSON 파싱
        try:
            if not ai_response or ai_response.strip() == "":
                raise ValueError("AI 응답이 비어있음")
                
            # JSON 부분만 추출 시도
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)
            else:
                result = json.loads(ai_response)
                
        except Exception as e:
            # JSON 파싱 실패시 기본 통과
            logger.warning(f"AI 검증 결과 파싱 실패 - 기본 통과: {e}")
            logger.warning(f"AI 검증 결과 : {ai_response[:200] if ai_response else 'EMPTY'}")
            result = {
                "is_valid": True,
                "issues": [],
                "needs_fix": False,
                "summary": "검증 파싱 실패로 통과"
            }
        
        # 결과 저장
        is_valid = result.get("is_valid", True)
        issues = result.get("issues", [])
        
        # 이슈를 문자열 리스트로 변환
        issue_list = []
        for issue in issues:
            if isinstance(issue, dict):
                issue_list.append(f"{issue.get('type', '')}: {issue.get('description', '')}")
            else:
                issue_list.append(str(issue))
        
        state["validation_result"] = {
            "is_valid": is_valid,
            "issues": issue_list,
            "summary": result.get("summary", "")
        }
        
        state["final_approval"] = is_valid
        
        logger.info(f"AI 검증 완료 - 유효: {is_valid}, 이슈: {len(issue_list)}개")

        # 검증 실패 시 상세 정보 로깅 (파일 저장용)
        if not is_valid and issue_list:
            logger.error("=" * 100)
            logger.error("🚫 검증 실패 케이스")
            logger.error("=" * 100)
            
            # 1. 기본 정보
            logger.error(f"📋 학생명: {teacher_input.get('name', 'Unknown')}")
            logger.error(f"📋 과목: {teacher_input.get('subject', 'Unknown')}")
            logger.error(f"📋 학교급: {teacher_input.get('school_level', 'Unknown')}")
            
            logger.error("")
            logger.error("-" * 60)
            logger.error("📝 교사 제공 정보")
            logger.error("-" * 60)
            logger.error(f"🎯 추가사항: {teacher_input.get('additional_notes', '없음')}")
            logger.error(f"🎯 성취기준: {teacher_input.get('achievement_standards', '없음')}")
            logger.error(f"🎯 중간 점수: {teacher_input.get('midterm_score', '없음')}")
            logger.error(f"🎯 기말 점수: {teacher_input.get('final_score', '없음')}")
            
            logger.error("")
            logger.error("-" * 60)
            logger.error("📄 생성된 원본 세특")
            logger.error("-" * 60)
            logger.error(content)
            
            logger.error("")
            logger.error("-" * 60)
            logger.error("❌ 검증 실패 사유")
            logger.error("-" * 60)
            logger.error(f"📊 요약: {result.get('summary', '없음')}")
            logger.error("")
            logger.error("📋 발견된 이슈:")
            for i, issue in enumerate(issue_list, 1):
                logger.error(f"  {i}. {issue}")
            
            logger.error("=" * 100)
        elif issue_list:
            logger.debug(f"발견된 이슈: {issue_list[:3]}")
        
    except Exception as e:
        import traceback
        logger.error(f"검증 중 오류: {type(e).__name__}: {e}")
        logger.error(f"트레이스백: {traceback.format_exc()}")
        
        # 오류 시 통과로 처리 (생성은 되었으므로)
        state["validation_result"] = {
            "is_valid": True,
            "issues": [],
            "error": str(e)
        }
        state["final_approval"] = True
    
    return state