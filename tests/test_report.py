"""Tests for the Report module."""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from simple_upgrade.report import ReportGenerator, generate_upgrade_report


class TestReportGenerator:
    """Test cases for ReportGenerator class."""

    def test_report_generator_initialization(self):
        """Test ReportGenerator initialization."""
        pre_checks = {'status': 'pending'}
        post_checks = {'status': 'pending'}

        generator = ReportGenerator(
            pre_checks=pre_checks,
            post_checks=post_checks
        )

        assert generator.pre_checks == pre_checks
        assert generator.post_checks == post_checks
        assert generator.upgrade_params == {}

    def test_report_generator_with_upgrade_params(self):
        """Test ReportGenerator with upgrade parameters."""
        pre_checks = {'status': 'pending'}
        post_checks = {'status': 'pending'}

        generator = ReportGenerator(
            pre_checks=pre_checks,
            post_checks=post_checks,
            upgrade_params={'version': '17.9.4', 'image': 'image.bin'}
        )

        assert generator.upgrade_params['version'] == '17.9.4'
        assert generator.upgrade_params['image'] == 'image.bin'

    def test_report_generator_compare_results_added(self):
        """Test compare_results detects added keys."""
        pre = {'key1': 'value1'}
        post = {'key1': 'value1', 'key2': 'value2'}

        generator = ReportGenerator(pre_checks={}, post_checks={})
        changes = generator.compare_results(pre, post)

        # Should find the added key
        added_changes = [c for c in changes if c['type'] == 'added']
        assert len(added_changes) == 1
        assert added_changes[0]['key'] == 'key2'

    def test_report_generator_compare_results_removed(self):
        """Test compare_results detects removed keys."""
        pre = {'key1': 'value1', 'key2': 'value2'}
        post = {'key1': 'value1'}

        generator = ReportGenerator(pre_checks={}, post_checks={})
        changes = generator.compare_results(pre, post)

        # Should find the removed key
        removed_changes = [c for c in changes if c['type'] == 'removed']
        assert len(removed_changes) == 1
        assert removed_changes[0]['key'] == 'key2'

    def test_report_generator_compare_results_modified(self):
        """Test compare_results detects modified keys."""
        pre = {'key1': 'value1'}
        post = {'key1': 'value2'}

        generator = ReportGenerator(pre_checks={}, post_checks={})
        changes = generator.compare_results(pre, post)

        # Should find the modified key
        modified_changes = [c for c in changes if c['type'] == 'modified']
        assert len(modified_changes) == 1
        assert modified_changes[0]['before'] == 'value1'
        assert modified_changes[0]['after'] == 'value2'

    def test_report_generator_generate_change_summary(self):
        """Test generate_change_summary method."""
        pre_checks = {'pre_upgrade': {'version': '17.9.3', 'interfaces': {}}}
        post_checks = {'post_upgrade': {'version': '17.9.4', 'interfaces': {}}}

        generator = ReportGenerator(
            pre_checks=pre_checks,
            post_checks=post_checks
        )

        summary = generator.generate_change_summary()

        assert 'total_changes' in summary
        assert 'categories' in summary
        assert summary['total_changes'] >= 0

    def test_report_generator_identify_issues_empty(self):
        """Test identify_issues returns empty when no issues."""
        pre_checks = {'status': 'passed'}
        post_checks = {'status': 'passed'}

        generator = ReportGenerator(
            pre_checks=pre_checks,
            post_checks=post_checks
        )

        issues = generator.identify_issues()
        assert isinstance(issues, list)
        assert len(issues) == 0

    def test_report_generator_identify_issues_pre_failed(self):
        """Test identify_issues detects pre-check failures."""
        pre_checks = {'status': 'failed'}
        post_checks = {'status': 'pending'}

        generator = ReportGenerator(
            pre_checks=pre_checks,
            post_checks=post_checks
        )

        issues = generator.identify_issues()
        assert len(issues) >= 1

    def test_report_generator_identify_issues_post_failed(self):
        """Test identify_issues detects post-check failures."""
        pre_checks = {'status': 'passed'}
        post_checks = {'status': 'failed'}

        generator = ReportGenerator(
            pre_checks=pre_checks,
            post_checks=post_checks
        )

        issues = generator.identify_issues()
        assert len(issues) >= 1

    def test_report_generator_generate_recommendations(self):
        """Test generate_recommendations method."""
        pre_checks = {'status': 'passed'}
        post_checks = {'status': 'passed'}

        generator = ReportGenerator(
            pre_checks=pre_checks,
            post_checks=post_checks
        )

        recommendations = generator.generate_recommendations()
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0

        # Check for common recommendations
        recommendation_texts = [r['recommendation'] for r in recommendations]
        assert any('version' in r.lower() for r in recommendation_texts)

    def test_report_generator_generate_report(self):
        """Test generate_report method."""
        pre_checks = {'status': 'passed'}
        post_checks = {'status': 'passed'}

        generator = ReportGenerator(
            pre_checks=pre_checks,
            post_checks=post_checks
        )

        report = generator.generate_report()

        assert 'metadata' in report
        assert 'executive_summary' in report
        assert 'change_summary' in report
        assert 'issues' in report
        assert 'recommendations' in report
        assert 'detailed_findings' in report

    def test_report_generator_save_report_json(self):
        """Test save_report with JSON format."""
        import tempfile
        import os

        pre_checks = {'status': 'passed'}
        post_checks = {'status': 'passed'}

        generator = ReportGenerator(
            pre_checks=pre_checks,
            post_checks=post_checks
        )

        report = generator.generate_report()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name

        try:
            result = generator.save_report(report, temp_file, format='json')
            assert result is True

            # Verify file exists and is valid JSON
            with open(temp_file, 'r') as f:
                import json
                data = json.load(f)
                assert data['executive_summary']['status'] == 'completed'
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def test_report_generator_save_report_text(self):
        """Test save_report with text format."""
        import tempfile
        import os

        pre_checks = {'status': 'passed'}
        post_checks = {'status': 'passed'}

        generator = ReportGenerator(
            pre_checks=pre_checks,
            post_checks=post_checks
        )

        report = generator.generate_report()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            temp_file = f.name

        try:
            result = generator.save_report(report, temp_file, format='text')
            assert result is True

            # Verify file exists and has content
            with open(temp_file, 'r') as f:
                content = f.read()
                assert len(content) > 0
                assert 'EXECUTIVE SUMMARY' in content
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def test_report_generator_executive_summary(self):
        """Test executive summary in report."""
        pre_checks = {'status': 'passed'}
        post_checks = {'status': 'passed'}

        generator = ReportGenerator(
            pre_checks=pre_checks,
            post_checks=post_checks
        )

        report = generator.generate_report()
        exec_sum = report['executive_summary']

        assert 'status' in exec_sum
        assert 'changes_count' in exec_sum
        assert 'issues_count' in exec_sum
        assert 'recommendations_count' in exec_sum
        assert 'overall_health' in exec_sum


class TestGenerateUpgradeReport:
    """Test standalone generate_upgrade_report function."""

    def test_generate_upgrade_report_basic(self):
        """Test generate_upgrade_report with basic parameters."""
        pre_checks = {'status': 'passed'}
        post_checks = {'status': 'passed'}

        report = generate_upgrade_report(
            pre_checks=pre_checks,
            post_checks=post_checks
        )

        assert 'executive_summary' in report

    def test_generate_upgrade_report_with_params(self):
        """Test generate_upgrade_report with upgrade parameters."""
        pre_checks = {'status': 'passed'}
        post_checks = {'status': 'passed'}

        report = generate_upgrade_report(
            pre_checks=pre_checks,
            post_checks=post_checks,
            upgrade_params={'version': '17.9.4'},
            output_format='json'
        )

        assert report['metadata']['upgrade_params']['version'] == '17.9.4'

    def test_generate_upgrade_report_with_file(self):
        """Test generate_upgrade_report saves to file."""
        import tempfile
        import os

        pre_checks = {'status': 'passed'}
        post_checks = {'status': 'passed'}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            temp_file = f.name

        try:
            report = generate_upgrade_report(
                pre_checks=pre_checks,
                post_checks=post_checks,
                output_file=temp_file,
                output_format='text'
            )

            assert os.path.exists(temp_file)
            assert report is not None
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
