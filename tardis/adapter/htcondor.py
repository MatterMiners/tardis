from ..interfaces.batchsystemadapter import BatchSystemAdapter


class HTCondorAdapter(BatchSystemAdapter):
    def integrate_machine(self, dns_name):
        pass

    def get_allocation(self, dns_name):
        pass

    def get_machine_status(self, dns_name=None):
        pass
        # condor_status -attributes Name,State,Activity,Drain -json

    def get_utilization(self, dns_name):
        pass
