
from aicspylibczi import CziFile
import numpy as np
from bioio import BioImage
from lxml import etree
import warnings

def _extract_acquisition_time_from_subblock_metadata(
    subblock_metadata: str,
) -> np.datetime64 | None:
    """Extracts acquisition time from subblock metadata."""
    outlxml = etree.fromstring(subblock_metadata)
    acquisition_time_element = outlxml.find(".//AcquisitionTime")

    if acquisition_time_element is not None and acquisition_time_element.text:
        # Parse acquisition time using numpy's datetime64 because it supports high
        # precision time (sub-microsecond). This parsing treats timezone-less dates
        # as UTC, which is fine for computing durations.
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                "no explicit representation of timezones available",
                category=UserWarning,
            )
            return np.datetime64(str(acquisition_time_element.text))

    return None

def _frame_acquisition_times(
    czi: CziFile,
    scene_key : str = "I",
) -> list[dict]:
    """
    Returns the acquisition times for each subblock

    Parameters
    ----------
    czi: CziFile
        Open CziFile instance.

    Returns
    -------
    list[dict]:
        A dictionary of acquisition times for each subblock.
        Takes the form of dict(S=scene_index, T=time_index,..., time=np.datetime64).
    """
    # Pre-fill output with None so callers can distinguish missing values.

    acquisition_times : list[dict]= []

    for subblock_info, subblock_metadata in czi.read_subblock_metadata():
        acquisition_time = _extract_acquisition_time_from_subblock_metadata(
            subblock_metadata
        )
        if acquisition_time is None:
            continue
        
        d = {
            **subblock_info,
            "acquired_time": acquisition_time
        }
        d[scene_key] = d.pop("S")  
        acquisition_times.append(d)
    return acquisition_times

def frame_acquisition_times(image: BioImage) -> list[dict] | None:
    """
    Return the earliest acquisition time for each mosaic tile and timepoint.

    Returns
    -------
    list[dict]:
        A dictionary of acquisition times for each subblock.
        Takes the form of dict(S=scene_index, T=time_index,..., time=np.datetime64).
    """
    with image.reader._fs.open(image.reader._path) as open_resource:
        czi = CziFile(open_resource.f)
        return _frame_acquisition_times(
            czi=czi,
        )
