from tests.utilities.utilities import async_return
from tests.utilities.utilities import run_async
from tardis.adapters.batchsystems.slurm import SlurmAdapter

#  from tardis.adapters.batchsystems.slurm import slurm_status_updater
from tardis.interfaces.batchsystemadapter import MachineStatus

#  from tardis.exceptions.tardisexceptions import AsyncRunCommandFailure

#  from functools import partial
#  from shlex import quote
from unittest.mock import patch
from unittest import TestCase


class TestSlurmAdapter(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock_config_patcher = patch(
            "tardis.adapters.batchsystems.slurm.Configuration"
        )
        cls.mock_async_run_command_patcher = patch(
            "tardis.adapters.batchsystems.slurm.async_run_command"
        )
        cls.mock_config = cls.mock_config_patcher.start()
        cls.mock_async_run_command = cls.mock_async_run_command_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.mock_config_patcher.stop()
        cls.mock_async_run_command_patcher.stop()

    def setUp(self):
        self.cpu_ratio = 0.5
        self.memory_ratio = 0.75

        self.command = (
            'sinfo --format="%T %C %e %m %f %n" --partition nemo_vm_atlsch --noheader'
        )

        self.command_wo_options = (
            'sinfo --format="%T %C %e %m %f %n" --partition nemo_vm_atlsch --noheader'
        )

        # sinfo --partition=nemo_vm_atlsch --format="%T %C %e %m %f %n" -r --noheader
        # Machine (DNS name)
        #     %n
        # State
        #     %T
        #     Figure out which states to handle how.
        # DroneUuid
        #     potentially not necessary could be implemented as feature: Drone
        #     itself adds MOAB job id to the features
        #     %f
        # CPU Stuff
        #     %C
        #     Output: allocated/idle/other/total
        #     Parse and compute measure. Maybe adapt configuration format such that
        #     user can choose formula.
        # Memory Stuff
        #     %e: free memory
        #     %m: total memory
        #     Parse and compute measure. Maybe adapt configuration format such that
        #     user can choose formula.
        return_value = "\n".join(
            [
                f"mixed 2/2/0/4 6000 24000 NemoVM host-10-18-1-1",
                f"mixed 3/1/0/4 15853 22011 NemoVM host-10-18-1-2",
                f"mixed 1/3/0/4 18268 22011 NemoVM host-10-18-1-4",
                f"mixed 3/1/0/4 17803 22011 NemoVM host-10-18-1-7",
                f"draining 0/4/0/4 17803 22011 NemoVM draining_machine",
                f"idle 0/4/0/4 17803 22011 NemoVM idle_machine",
                f"drained 0/4/0/4 17803 22011 NemoVM drained_machine",
                f"powerup 0/4/0/4 17803 22011 NemoVM power_up_machine",
            ]
        )

        self.mock_async_run_command.return_value = async_return(
            return_value=return_value
        )

        self.setup_config_mock(options={"partition": "nemo_vm_atlsch"})

        self.slurm_adapter = SlurmAdapter()

    def tearDown(self):
        self.mock_async_run_command.reset_mock()

    def setup_config_mock(self, options=None):
        self.config = self.mock_config.return_value
        self.config.BatchSystem.ratios = {
            "cpu_ratio": "Real(TotalSlotCpus-Cpus)/TotalSlotCpus",
            "memory_ratio": "Real(TotalSlotMemory-Memory)/TotalSlotMemory",
        }
        self.config.BatchSystem.max_age = 10
        if options:
            self.config.BatchSystem.options = options
        else:
            self.config.BatchSystem.options = {}

    def test_disintegrate_machine(self):
        self.assertIsNone(
            run_async(self.slurm_adapter.disintegrate_machine, drone_uuid="test")
        )

    def test_drain_machine(self):
        run_async(self.slurm_adapter.drain_machine, drone_uuid="host-10-18-1-1")
        self.mock_async_run_command.assert_called_with(
            "scontrol update --partition nemo_vm_atlsch NodeName=host-10-18-1-1 State=DRAIN Reason='COBalD/TARDIS says so'"
        )
        self.assertIsNone(
            run_async(self.slurm_adapter.drain_machine, drone_uuid="not_exists")
        )
        #  # Does not work
        #  self.mock_async_run_command.side_effect = AsyncRunCommandFailure(
        #      message="Does not exists",
        #      error_code=1,
        #      error_message="Does not exists",
        #  )
        self.assertIsNone(
            run_async(self.slurm_adapter.drain_machine, drone_uuid="test")
        )

        # Does not work
        #  self.mock_async_run_command.side_effect = AsyncRunCommandFailure(
        #      message="Unhandled error",
        #      error_code=2,
        #      error_message="Unhandled error",
        #  )
        # Does not work
        #  with self.assertRaises(AsyncRunCommandFailure):
        #      self.assertIsNone(
        #          run_async(self.slurm_adapter.drain_machine, drone_uuid="test")
        #      )

        self.mock_async_run_command.side_effect = None

    def test_drain_machine_without_options(self):
        self.setup_config_mock()
        self.slurm_adapter = SlurmAdapter()

        run_async(self.slurm_adapter.drain_machine, drone_uuid="host-10-18-1-1")
        self.mock_async_run_command.assert_called_with(
            "scontrol update NodeName=host-10-18-1-1 State=DRAIN Reason='COBalD/TARDIS says so'"
        )

    def test_integrate_machine(self):
        self.assertIsNone(
            run_async(self.slurm_adapter.integrate_machine, drone_uuid="host-10-18-1-1")
        )

    def test_get_resource_ratios(self):
        self.assertCountEqual(
            list(
                run_async(
                    self.slurm_adapter.get_resource_ratios, drone_uuid="host-10-18-1-1"
                )
            ),
            [self.cpu_ratio, self.memory_ratio],
        )
        self.mock_async_run_command.assert_called_with(self.command)

        self.assertEqual(
            run_async(self.slurm_adapter.get_resource_ratios, drone_uuid="not_exists"),
            {},
        )

    def test_get_resource_ratios_without_options(self):
        self.setup_config_mock()
        del self.config.BatchSystem.options
        self.slurm_adapter = SlurmAdapter()

        self.assertCountEqual(
            list(
                run_async(
                    self.slurm_adapter.get_resource_ratios, drone_uuid="host-10-18-1-1"
                )
            ),
            [self.cpu_ratio, self.memory_ratio],
        )

        self.mock_async_run_command.assert_called_with(self.command_wo_options)

    def test_get_allocation(self):
        self.assertEqual(
            run_async(self.slurm_adapter.get_allocation, drone_uuid="host-10-18-1-1"),
            max([self.cpu_ratio, self.memory_ratio]),
        )
        self.mock_async_run_command.assert_called_with(self.command)

    def test_get_machine_status(self):
        self.assertEqual(
            run_async(
                self.slurm_adapter.get_machine_status, drone_uuid="host-10-18-1-1"
            ),
            MachineStatus.Available,
        )
        self.mock_async_run_command.assert_called_with(self.command)
        self.mock_async_run_command.reset_mock()
        self.assertEqual(
            run_async(self.slurm_adapter.get_machine_status, drone_uuid="not_exists"),
            MachineStatus.NotAvailable,
        )
        self.mock_async_run_command.reset_mock()
        self.assertEqual(
            run_async(
                self.slurm_adapter.get_machine_status, drone_uuid="draining_machine"
            ),
            MachineStatus.Draining,
        )
        self.mock_async_run_command.reset_mock()
        self.assertEqual(
            run_async(self.slurm_adapter.get_machine_status, drone_uuid="idle_machine"),
            MachineStatus.Draining,
        )
        self.mock_async_run_command.reset_mock()
        self.assertEqual(
            run_async(
                self.slurm_adapter.get_machine_status, drone_uuid="drained_machine"
            ),
            MachineStatus.Drained,
        )
        self.mock_async_run_command.reset_mock()
        self.assertEqual(
            run_async(
                self.slurm_adapter.get_machine_status, drone_uuid="power_up_machine"
            ),
            MachineStatus.NotAvailable,
        )
        self.mock_async_run_command.reset_mock()

        self.assertEqual(
            run_async(
                self.slurm_adapter.get_machine_status, drone_uuid="host-10-18-1-1"
            ),
            MachineStatus.Available,
        )
        self.mock_async_run_command.reset_mock()

        # TODO: Not sure yet what this is doing
        #  self.mock_async_run_command.side_effect = AsyncRunCommandFailure(
        #      message="Test", error_code=123, error_message="Test"
        #  )
        #  with self.assertLogs(level="ERROR"):
        #      attributes = dict(
        #          Machine="Machine",
        #          State="State",
        #          Activity="Activity",
        #          TardisDroneUuid="TardisDroneUuid",
        #      )
        #      # Escape slurm expressions and add them to attributes
        #      attributes.update(
        #          {
        #              key: quote(value)
        #              for key, value in self.config.BatchSystem.ratios.items()
        #          }
        #      )
        #
        #      run_async(
        #          partial(
        #              slurm_status_updater, self.config.BatchSystem.options, attributes
        #          )
        #      )
        #      self.mock_async_run_command.assert_called_with(self.command)
        #  self.mock_async_run_command.side_effect = None

    def test_get_utilization(self):
        self.assertEqual(
            run_async(self.slurm_adapter.get_utilization, drone_uuid="host-10-18-1-1"),
            min([self.cpu_ratio, self.memory_ratio]),
        )
        self.mock_async_run_command.assert_called_with(self.command)
