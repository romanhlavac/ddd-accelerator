from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[3]
TARGET = ROOT / 'scaffolds' / 'miro' / 'rem-012-3-5-frame-00.yaml'


def load():
    return yaml.safe_load(TARGET.read_text(encoding='utf-8'))


def luminance(value: str) -> float:
    rgb = [int(value[i:i+2], 16) / 255 for i in (1, 3, 5)]
    linear = [x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4 for x in rgb]
    return .2126 * linear[0] + .7152 * linear[1] + .0722 * linear[2]


def test_exact_scope_and_lineage():
    data = load()
    assert data['remediation_id'] == 'REM-PR8-HVA-CC-012.3.5'
    assert data['authorized_predecessor_sha'] == 'e4b0c99f21517a9291a165cbb38d17cb57241fa1'
    assert data['frame_id'] == '3458764679756478046'
    assert len(data['protected_frame_ids']) == 17


def test_summary_contains_all_maturity_counts_and_flags():
    text = load()['fixed_items']['summary']['content']
    for phrase in ('SCAFFOLD: 1', 'WORKING: 2', 'CANDIDATE: 0', 'VALIDATED: 0', 'ACCEPTED: 0', 'SUPERSEDED: 0', 'ATTENTION: 1', 'BLOCKING: 0'):
        assert phrase in text
    assert '…' not in text


def test_summary_markers_are_small_and_inside_card():
    data = load()
    summary = data['fixed_items']['summary']
    left = summary['x'] - summary['width'] / 2
    right = summary['x'] + summary['width'] / 2
    top = summary['y'] - summary['height'] / 2
    bottom = summary['y'] + summary['height'] / 2
    assert len(data['summary_markers']) == 6
    for marker in data['summary_markers']:
        assert marker['width'] <= 80 and marker['height'] <= 80
        assert left <= marker['x'] - marker['width'] / 2
        assert marker['x'] + marker['width'] / 2 <= right
        assert top <= marker['y'] - marker['height'] / 2
        assert marker['y'] + marker['height'] / 2 <= bottom


def test_palette_is_light_to_dark_and_shared_by_both_marker_sets():
    data = load()
    keys = ['scaffold', 'working', 'candidate', 'validated', 'accepted', 'superseded']
    values = [data['palette'][key] for key in keys]
    levels = [luminance(value) for value in values]
    assert len(set(values)) == 6
    assert all(a > b for a, b in zip(levels, levels[1:]))
    assert [x['key'] for x in data['summary_markers']] == keys
    assert [x['key'] for x in data['legend_markers']] == keys


def test_bottom_legend_explains_each_state_instead_of_color_scale():
    data = load()
    legend = data['fixed_items']['legend']['content']
    expected = {
        'SCAFFOLD': 'založená počáteční struktura',
        'WORKING': 'aktivně rozpracovaná pracovní verze',
        'CANDIDATE': 'připravená k formálnímu review',
        'VALIDATED': 'prošla technickou a metodickou validací',
        'ACCEPTED': 'člověkem přijatá pro další použití',
        'SUPERSEDED': 'nahrazená novější verzí',
    }
    for state, explanation in expected.items():
        assert state in legend and explanation in legend
    for phrase in data['forbidden_phrases']:
        assert phrase not in legend
    assert len(data['legend_markers']) == 6
    assert all(x['width'] <= 50 and x['height'] <= 50 for x in data['legend_markers'])
