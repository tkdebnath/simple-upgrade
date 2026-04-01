"""
Report module - Compare pre/post upgrade checks and generate detailed reports.

This module provides functionality to compare pre-upgrade and post-upgrade
check results and generate comprehensive reports highlighting changes,
issues, and recommendations.

Usage:
    from simple_upgrade import ReportGenerator

    generator = ReportGenerator(
        pre_checks=pre_results,
        post_checks=post_results
    )

    report = generator.generate_report()
    generator.save_report(report, "upgrade_report.txt")
"""

from typing import Dict, Any, List, Optional
import datetime
import json


class ReportGenerator:
    """
    Compares pre-upgrade and post-upgrade results and generates detailed reports.

    Generates reports with:
        - Executive summary
        - Change summary (before/after comparison)
        - Issue identification
        - Recommendations
        - Detailed findings
    """

    def __init__(
        self,
        pre_checks: Dict[str, Any],
        post_checks: Dict[str, Any],
        upgrade_params: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the ReportGenerator.

        Args:
            pre_checks: Results from pre-upgrade checks
            post_checks: Results from post-upgrade checks
            upgrade_params: Dictionary with upgrade parameters (version, image, etc.)
        """
        self.pre_checks = pre_checks
        self.post_checks = post_checks
        self.upgrade_params = upgrade_params or {}

        self.report: Dict[str, Any] = {}
        self.changes: List[Dict[str, Any]] = []
        self.issues: List[Dict[str, Any]] = []
        self.recommendations: List[Dict[str, Any]] = []

    def compare_results(self, pre: Dict[str, Any], post: Dict[str, Any], key: str = "") -> List[Dict[str, Any]]:
        """
        Recursively compare pre and post results to find changes.

        Args:
            pre: Pre-upgrade results
            post: Post-upgrade results
            key: Current key path for nested structures

        Returns:
            List of change dictionaries
        """
        changes = []

        if isinstance(pre, dict) and isinstance(post, dict):
            for k in set(pre.keys()) | set(post.keys()):
                new_key = f"{key}.{k}" if key else k

                if k not in pre:
                    changes.append({
                        'key': new_key,
                        'type': 'added',
                        'before': None,
                        'after': post.get(k),
                    })
                elif k not in post:
                    changes.append({
                        'key': new_key,
                        'type': 'removed',
                        'before': pre.get(k),
                        'after': None,
                    })
                else:
                    changes.extend(self.compare_results(pre[k], post[k], new_key))
        elif pre != post:
            changes.append({
                'key': key,
                'type': 'modified',
                'before': pre,
                'after': post,
            })

        return changes

    def generate_change_summary(self) -> Dict[str, Any]:
        """
        Generate a summary of changes between pre and post checks.

        Returns:
            Dictionary with change summary
        """
        summary = {
            'total_changes': 0,
            'categories': {},
            'details': [],
        }

        # Compare pre and post check results
        changes = self.compare_results(self.pre_checks, self.post_checks)

        # Categorize changes
        for change in changes:
            change_type = change['type']
            key = change['key']

            # Determine category based on key
            category = 'general'
            if 'version' in key.lower():
                category = 'software'
            elif 'interface' in key.lower():
                category = 'interfaces'
            elif 'bgp' in key.lower():
                category = 'bgp'
            elif 'ospf' in key.lower():
                category = 'ospf'
            elif 'mac' in key.lower():
                category = 'mac'
            elif 'arp' in key.lower():
                category = 'arp'
            elif 'uptime' in key.lower():
                category = 'uptime'
            elif 'free_space' in key.lower() or 'storage' in key.lower():
                category = 'storage'

            if category not in summary['categories']:
                summary['categories'][category] = {
                    'added': 0,
                    'removed': 0,
                    'modified': 0,
                    'total': 0,
                }

            summary['categories'][category][change_type] += 1
            summary['categories'][category]['total'] += 1
            summary['total_changes'] += 1

            # Add detail for modifications
            if change_type == 'modified':
                summary['details'].append({
                    'key': key,
                    'before': change['before'],
                    'after': change['after'],
                    'category': category,
                })

        return summary

    def identify_issues(self) -> List[Dict[str, Any]]:
        """
        Identify issues from pre and post check results.

        Returns:
            List of issue dictionaries
        """
        issues = []

        # Check for issues in pre-checks
        if self.pre_checks:
            pre_status = self.pre_checks.get('status', 'pending')
            if pre_status in ['warning', 'failed']:
                issues.append({
                    'severity': 'high' if pre_status == 'failed' else 'medium',
                    'category': 'pre_upgrade',
                    'description': f"Pre-upgrade checks {pre_status}",
                    'details': self.pre_checks,
                })

        # Check for issues in post-checks
        if self.post_checks:
            post_status = self.post_checks.get('status', 'pending')
            if post_status in ['warning', 'failed']:
                issues.append({
                    'severity': 'high' if post_status == 'failed' else 'medium',
                    'category': 'post_upgrade',
                    'description': f"Post-upgrade checks {post_status}",
                    'details': self.post_checks,
                })

        # Check for specific issue categories
        issues.extend(self._check_interface_issues())
        issues.extend(self._check_bgp_issues())
        issues.extend(self._check_version_issues())

        return issues

    def _check_interface_issues(self) -> List[Dict[str, Any]]:
        """Check for interface-related issues."""
        issues = []

        pre_ifaces = self.pre_checks.get('pre_upgrade', {}).get('interfaces', {})
        post_ifaces = self.post_checks.get('post_upgrade', {}).get('interfaces', {})

        # Check for interface flaps
        if pre_ifaces and post_ifaces:
            for iface, config in pre_ifaces.items():
                if config.get('oper_status') == 'up':
                    if post_ifaces.get(iface, {}).get('oper_status') == 'down':
                        issues.append({
                            'severity': 'high',
                            'category': 'interfaces',
                            'description': f"Interface {iface} went down after upgrade",
                        })

        return issues

    def _check_bgp_issues(self) -> List[Dict[str, Any]]:
        """Check for BGP-related issues."""
        issues = []

        pre_bgp = self.pre_checks.get('pre_upgrade', {}).get('bgp_peers', {})
        post_bgp = self.post_checks.get('post_upgrade', {}).get('bgp_peers', {})

        # Check for BGP neighbor state changes
        if pre_bgp and post_bgp:
            for peer, state in pre_bgp.items():
                if state == 'established':
                    if post_bgp.get(peer) != 'established':
                        issues.append({
                            'severity': 'high',
                            'category': 'bgp',
                            'description': f"BGP peer {peer} state changed from established to {post_bgp.get(peer, 'unknown')}",
                        })

        return issues

    def _check_version_issues(self) -> List[Dict[str, Any]]:
        """Check for version-related issues."""
        issues = []

        pre_version = self.pre_checks.get('pre_upgrade', {}).get('current_version', {})
        post_version = self.post_checks.get('post_upgrade', {}).get('version', {})

        pre_ver = pre_version.get('current_version', '') if isinstance(pre_version, dict) else pre_version
        post_ver = post_version.get('current_version', '') if isinstance(post_version, dict) else post_version

        # Check if version actually changed
        target_version = self.upgrade_params.get('version', '')
        if target_version and post_ver != target_version:
            issues.append({
                'severity': 'high',
                'category': 'software',
                'description': f"Version mismatch - expected {target_version}, got {post_ver}",
            })

        return issues

    def generate_recommendations(self) -> List[Dict[str, Any]]:
        """
        Generate recommendations based on check results.

        Returns:
            List of recommendation dictionaries
        """
        recommendations = []

        # Check version
        if self.upgrade_params.get('version'):
            recommendations.append({
                'category': 'software',
                'priority': 'high',
                'recommendation': f"Verify that version {self.upgrade_params['version']} is functioning correctly",
                'rationale': "Confirm the upgrade achieved the desired version",
            })

        # Check for issues
        if self.issues:
            recommendations.append({
                'category': 'general',
                'priority': 'high',
                'recommendation': "Review all identified issues and resolve before returning device to production",
                'rationale': "Issues detected during upgrade process may impact stability",
            })

        # Check for configuration changes
        recommendations.append({
            'category': 'configuration',
            'priority': 'medium',
            'recommendation': "Compare running configuration with pre-upgrade backup",
            'rationale': "Ensure no unexpected configuration changes occurred",
        })

        # Check for monitoring
        recommendations.append({
            'category': 'monitoring',
            'priority': 'medium',
            'recommendation': "Enable enhanced monitoring for 24-48 hours post-upgrade",
            'rationale': "Detect any delayed issues or performance degradation",
        })

        return recommendations

    def generate_report(self) -> Dict[str, Any]:
        """
        Generate the complete upgrade report.

        Returns:
            Dictionary containing the full report
        """
        # Generate components
        change_summary = self.generate_change_summary()
        self.issues = self.identify_issues()
        self.recommendations = self.generate_recommendations()

        # Build report
        self.report = {
            'metadata': {
                'generated_at': datetime.datetime.now().isoformat(),
                'upgrade_params': self.upgrade_params,
            },
            'executive_summary': {
                'status': 'completed',
                'changes_count': change_summary['total_changes'],
                'issues_count': len(self.issues),
                'recommendations_count': len(self.recommendations),
                'overall_health': 'healthy' if not self.issues else 'at_risk',
            },
            'change_summary': change_summary,
            'issues': self.issues,
            'recommendations': self.recommendations,
            'pre_check_results': self.pre_checks,
            'post_check_results': self.post_checks,
            'detailed_findings': self._generate_detailed_findings(change_summary),
        }

        return self.report

    def _generate_detailed_findings(self, change_summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate detailed findings section.

        Args:
            change_summary: The change summary dictionary

        Returns:
            Dictionary with detailed findings
        """
        return {
            'change_categories': change_summary['categories'],
            'modified_values': change_summary['details'],
            'issue_breakdown': {
                'by_severity': {},
                'by_category': {},
            },
            'recommendation_breakdown': {
                'by_priority': {},
                'by_category': {},
            },
        }

    def save_report(self, report: Dict[str, Any], filename: str, format: str = 'json') -> bool:
        """
        Save report to file.

        Args:
            report: Report dictionary to save
            filename: Output filename
            format: Output format ('json' or 'text')

        Returns:
            True if successful, False otherwise
        """
        try:
            if format == 'json':
                with open(filename, 'w') as f:
                    json.dump(report, f, indent=2, default=str)
            elif format == 'text':
                with open(filename, 'w') as f:
                    f.write(self._format_text_report(report))
            return True
        except Exception as e:
            return False

    def _format_text_report(self, report: Dict[str, Any]) -> str:
        """
        Format report as human-readable text.

        Args:
            report: Report dictionary

        Returns:
            Formatted text string
        """
        lines = []

        # Header
        lines.append("=" * 80)
        lines.append("NETWORK UPGRADE VERIFICATION REPORT")
        lines.append("=" * 80)
        lines.append(f"Generated: {report['metadata']['generated_at']}")
        lines.append(f"Upgrade Version: {report['metadata']['upgrade_params'].get('version', 'N/A')}")
        lines.append("")

        # Executive Summary
        lines.append("-" * 40)
        lines.append("EXECUTIVE SUMMARY")
        lines.append("-" * 40)
        exec_sum = report['executive_summary']
        lines.append(f"Status: {exec_sum['overall_health'].upper()}")
        lines.append(f"Changes Detected: {exec_sum['changes_count']}")
        lines.append(f"Issues Found: {exec_sum['issues_count']}")
        lines.append(f"Recommendations: {exec_sum['recommendations_count']}")
        lines.append("")

        # Change Summary
        if report['change_summary']['total_changes'] > 0:
            lines.append("-" * 40)
            lines.append("CHANGE SUMMARY")
            lines.append("-" * 40)
            for category, stats in report['change_summary']['categories'].items():
                lines.append(f"{category}: +{stats['added']} -{stats['removed']} ~{stats['modified']}")
            lines.append("")

        # Issues
        if report['issues']:
            lines.append("-" * 40)
            lines.append("ISSUES")
            lines.append("-" * 40)
            for issue in report['issues']:
                lines.append(f"[{issue['severity'].upper()}] {issue['description']}")
                lines.append(f"  Category: {issue['category']}")
                if 'details' in issue:
                    lines.append(f"  Details: {issue['details']}")
            lines.append("")

        # Recommendations
        if report['recommendations']:
            lines.append("-" * 40)
            lines.append("RECOMMENDATIONS")
            lines.append("-" * 40)
            for rec in report['recommendations']:
                lines.append(f"[{rec['priority'].upper()}] {rec['recommendation']}")
                lines.append(f"  Rationale: {rec['rationale']}")
            lines.append("")

        return "\n".join(lines)


def generate_upgrade_report(
    pre_checks: Dict[str, Any],
    post_checks: Dict[str, Any],
    upgrade_params: Optional[Dict[str, Any]] = None,
    output_file: Optional[str] = None,
    output_format: str = 'json',
) -> Dict[str, Any]:
    """
    Standalone function to generate upgrade report.

    Args:
        pre_checks: Pre-upgrade check results
        post_checks: Post-upgrade check results
        upgrade_params: Upgrade parameters
        output_file: Optional file to save report
        output_format: Output format ('json' or 'text')

    Returns:
        Report dictionary
    """
    generator = ReportGenerator(
        pre_checks=pre_checks,
        post_checks=post_checks,
        upgrade_params=upgrade_params,
    )

    report = generator.generate_report()

    if output_file:
        generator.save_report(report, output_file, output_format)

    return report
