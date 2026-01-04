"""Renderer and parser for analysis results, ported from argumentanalyzer."""

import json
import re
from typing import Any

from src.utils.logger import get_logger

logger = get_logger(__name__)


def parse_json_output(output: str) -> dict[str, Any]:
    """Extract and parse JSON from agent output."""
    try:
        # Try direct parsing first
        return json.loads(output)
    except json.JSONDecodeError:
        # Try to find JSON block in markdown
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', output, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find anything that looks like a JSON object
        json_match = re.search(r'(\{.*\})', output, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

    # Log the failure with raw output for debugging
    logger.warning(f"Failed to parse JSON from output: {output[:500]}...")
    return {"error": "Could not parse JSON output", "raw": output}


class ReportRenderer:
    """Renderer for converting analysis JSON to HTML components."""

    def render_source_assessment(self, data: dict[str, Any]) -> str:
        """Render source credibility assessment."""
        assessment = data.get("source_assessment", {})
        credibility = assessment.get("credibility", "unknown").lower()
        
        colors = {
            "high": "text-green-600 bg-green-50 border-green-200",
            "medium": "text-yellow-600 bg-yellow-50 border-yellow-200",
            "low": "text-red-600 bg-red-50 border-red-200",
            "unknown": "text-gray-600 bg-gray-50 border-gray-200"
        }
        color_class = colors.get(credibility, colors["unknown"])
        
        html = f"""
        <div class="p-4 rounded-lg border {color_class} mb-6">
            <h3 class="text-lg font-bold mb-2">Source Assessment: {credibility.capitalize()}</h3>
            <p class="mb-3">{assessment.get('reasoning', 'No reasoning provided.')}</p>
            {self._render_list("Potential Biases", assessment.get('potential_biases', []))}
        </div>
        """
        return html

    def render_summary(self, data: dict[str, Any]) -> str:
        """Render content summary."""
        summary_text = data.get('summary', '').replace('\n', '<br>')
        key_points_html = " ".join([f'<li><span class="font-medium text-blue-600">{p.get("location", "")}</span> {p.get("point", "")}</li>' for p in data.get('key_points', [])])
        conclusions_html = " ".join([f'<li>{c}</li>' for c in data.get('conclusions', [])])
        
        html = f"""
        <div class="mb-8">
            <h2 class="text-2xl font-bold mb-4">Summary</h2>
            <div class="prose max-w-none text-gray-700 mb-6">
                {summary_text}
            </div>
            
            <div class="grid md:grid-cols-2 gap-6">
                <div>
                    <h3 class="text-lg font-semibold mb-3">Key Points</h3>
                    <ul class="space-y-2">
                        {key_points_html}
                    </ul>
                </div>
                <div>
                    <h3 class="text-lg font-semibold mb-3">Main Argument</h3>
                    <p class="italic text-gray-700">{data.get('main_argument', 'N/A')}</p>
                    
                    <h3 class="text-lg font-semibold mt-4 mb-2">Conclusions</h3>
                    <ul class="list-disc list-inside space-y-1 text-gray-700">
                        {conclusions_html}
                    </ul>
                </div>
            </div>
        </div>
        """
        return html

    def render_claims(self, data: dict[str, Any]) -> str:
        """Render extracted claims with evidence."""
        type_colors = {
            "factual": "bg-blue-100 text-blue-700",
            "unsupported": "bg-yellow-100 text-yellow-700",
            "opinion": "bg-purple-100 text-purple-700",
            "prediction": "bg-orange-100 text-orange-700"
        }

        html = f"""
        <div class="mb-8">
            <h2 class="text-2xl font-bold mb-4">Key Claims</h2>
            <ul class="space-y-3">
                {" ".join([f'''
                    <li class="p-3 bg-white rounded border border-gray-100 shadow-sm">
                        <div class="flex items-start gap-2">
                            <span class="px-2 py-0.5 rounded-full text-xs font-bold uppercase {type_colors.get(c.get('type', 'unsupported'), type_colors['unsupported'])} flex-shrink-0">
                                {c.get('type', 'unsupported')}
                            </span>
                            <div>
                                <div class="font-medium">{c.get('text', '')}</div>
                                <div class="text-xs text-gray-500 mt-1 italic">
                                    Evidence: {c.get('evidence', 'Not analyzed')}
                                </div>
                            </div>
                        </div>
                    </li>
                ''' for c in data.get('claims', [])])}
            </ul>
        </div>
        """
        return html

    def render_controversy(self, data: dict[str, Any]) -> str:
        """Render controversy and conspiracy indicators."""
        views = data.get("controversial_views", [])
        indicators = data.get("conspiracy_indicators", [])
        assessment = data.get("overall_assessment", {})
        
        if not views and not indicators:
            return ""
            
        html = f"""
        <div class="mb-8 p-6 bg-red-50 rounded-xl border border-red-100">
            <h2 class="text-2xl font-bold text-red-900 mb-4">Controversial Content Analysis</h2>
            
            <div class="mb-4">
                <span class="font-bold">Level:</span> 
                <span class="px-3 py-1 bg-red-100 text-red-700 rounded-full font-bold ml-2">
                    {assessment.get('controversy_level', 'Unknown').upper()}
                </span>
            </div>
            
            <p class="mb-6 text-red-800">{assessment.get('summary', '')}</p>
            
            {self._render_controversy_items("Views on Institutions", views)}
            {self._render_conspiracy_items("Conspiracy Indicators", indicators)}
        </div>
        """
        return html

    def render_fallacies(self, data: dict[str, Any]) -> str:
        """Render detected logical fallacies."""
        fallacies = data.get("fallacies", [])
        if not fallacies:
            return ""
            
        html = f"""
        <div class="mb-8">
            <h2 class="text-2xl font-bold mb-4">Logical Fallacy Detection</h2>
            <div class="mb-4">
                <span class="font-bold">Reasoning Quality:</span> 
                <span class="px-3 py-1 bg-blue-100 text-blue-700 rounded-full font-bold ml-2">
                    {data.get('overall_reasoning_quality', 'Unknown').upper()}
                </span>
            </div>
            
            <div class="grid gap-4">
                {" ".join([f'''
                    <div class="p-4 bg-white rounded-lg border-l-4 border-red-500 shadow-sm">
                        <h4 class="font-bold text-red-700 mb-1">{f.get('type', 'Logical Fallacy')}</h4>
                        <p class="text-sm italic text-gray-600 mb-2">"{f.get('quote', '')}" ({f.get('location', '')})</p>
                        <p class="text-gray-700">{f.get('explanation', '')}</p>
                    </div>
                ''' for f in fallacies])}
            </div>
        </div>
        """
        return html

    def render_counterargument(self, data: dict[str, Any]) -> str:
        """Render the primary counterargument and sources."""
        html = f"""
        <div class="mb-8 p-6 bg-blue-50 rounded-xl border border-blue-100">
            <h2 class="text-2xl font-bold text-blue-900 mb-4">Counter-Perspectives</h2>
            
            <div class="mb-4">
                <h3 class="text-lg font-semibold text-blue-800 mb-2">The Counterargument</h3>
                <div class="prose max-w-none text-blue-900">
                    {data.get('counterargument', '')}
                </div>
            </div>
            
            <div>
                <h3 class="text-sm font-bold uppercase text-blue-700 mb-2">Sourced from</h3>
                <div class="flex flex-wrap gap-3">
                    {" ".join([f'''
                        <a href="{s.get('url', '#')}" target="_blank" class="text-sm text-blue-600 hover:underline flex items-center">
                            {s.get('title', 'Source')}
                            <svg class="w-3 h-3 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
                        </a>
                    ''' for s in data.get('sources', [])])}
                </div>
            </div>
        </div>
        """
        return html

    def _render_list(self, title: str, items: list[str]) -> str:
        if not items: return ""
        return f"""
        <div class="mt-2">
            <span class="font-bold text-sm uppercase">{title}:</span>
            <div class="flex flex-wrap gap-1 mt-1">
                {" ".join([f'<span class="text-xs px-2 py-0.5 bg-white/50 rounded">{i}</span>' for i in items])}
            </div>
        </div>
        """

    def _render_controversy_items(self, title: str, items: list[dict]) -> str:
        if not items: return ""
        return f"""
        <div class="mb-4">
            <h4 class="font-bold text-red-900 mb-2">{title}</h4>
            <div class="space-y-2">
                {" ".join([f'''
                    <div class="text-sm p-3 bg-white/40 rounded border border-red-200">
                        <span class="font-bold">{i.get('target', '')}:</span> {i.get('claim_text', '')}
                        <div class="text-xs mt-1 text-red-700 italic">{i.get('reasoning', '')}</div>
                    </div>
                ''' for i in items])}
            </div>
        </div>
        """

    def _render_conspiracy_items(self, title: str, items: list[dict]) -> str:
        if not items: return ""
        return f"""
        <div class="">
            <h4 class="font-bold text-red-900 mb-2">{title}</h4>
            <div class="space-y-2">
                {" ".join([f'''
                    <div class="text-sm p-3 bg-white/40 rounded border border-red-200">
                        <span class="font-bold">{i.get('pattern', '')}:</span> {i.get('evidence', '')}
                        <div class="text-xs mt-1 text-red-700 italic">Quote: "{i.get('quote', '')}"</div>
                    </div>
                ''' for i in items])}
            </div>
        </div>
        """
