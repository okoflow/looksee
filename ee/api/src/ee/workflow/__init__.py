"""Commercial workflow node types, registered into the api node unions."""

from api.domain.workflow.extensions import NodeExtension
from ee.features import ENTERPRISE_INTEGRATIONS, MEASUREMENT_FILTERS
from ee.workflow.actions import RunnableSlackAction, SlackActionData
from ee.workflow.filters import (
    CountThresholdFilterData,
    DwellFilterData,
    LineCrossingFilterData,
    RunnableDwellFilter,
    RunnableLineCrossingFilter,
)

NODE_EXTENSIONS: tuple[NodeExtension, ...] = (
    NodeExtension(
        kind="line_crossing_filter",
        feature=MEASUREMENT_FILTERS,
        draft=LineCrossingFilterData,
        runnable=RunnableLineCrossingFilter,
    ),
    NodeExtension(
        kind="dwell_filter",
        feature=MEASUREMENT_FILTERS,
        draft=DwellFilterData,
        runnable=RunnableDwellFilter,
    ),
    NodeExtension(
        kind="count_threshold_filter",
        feature=MEASUREMENT_FILTERS,
        draft=CountThresholdFilterData,
        runnable=CountThresholdFilterData,
    ),
    NodeExtension(
        kind="slack_action",
        feature=ENTERPRISE_INTEGRATIONS,
        draft=SlackActionData,
        runnable=RunnableSlackAction,
        deliver="ee.adapters.delivery:run_slack",
    ),
)
