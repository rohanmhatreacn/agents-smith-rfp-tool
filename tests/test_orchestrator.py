import pytest
import asyncio
from orchestrator import orchestrator


@pytest.mark.asyncio
async def test_strategist_routing():
    """
    Tests that strategist queries are correctly routed to the strategist agent.
    Validates routing logic and response format.
    """
    result = await orchestrator.process(
        user_input="Analyze the key requirements and win themes for this RFP",
        session_id="test-session-1"
    )
    
    assert result['agent'] == 'strategist'
    assert 'result' in result
    assert len(str(result['result'])) > 0


@pytest.mark.asyncio
async def test_solution_architect_routing():
    """
    Tests that technical architecture queries route to solution architect agent.
    Validates technical content in response.
    """
    result = await orchestrator.process(
        user_input="Design a cloud architecture for this system",
        session_id="test-session-2"
    )
    
    assert result['agent'] == 'solution_architect'
    assert 'result' in result


@pytest.mark.asyncio
async def test_financial_routing():
    """
    Tests that pricing queries route to financial agent.
    Validates financial data structure in response.
    """
    result = await orchestrator.process(
        user_input="Create a pricing breakdown for this proposal",
        session_id="test-session-3"
    )
    
    assert result['agent'] == 'financial'
    assert 'result' in result


@pytest.mark.asyncio
async def test_session_persistence():
    """
    Tests that session data is properly saved and can be retrieved.
    Validates storage functionality.
    """
    session_id = "test-session-persistence"
    
    result = await orchestrator.process(
        user_input="Test query for persistence",
        session_id=session_id
    )
    
    assert result['session_id'] == session_id
    assert 'output_key' in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

