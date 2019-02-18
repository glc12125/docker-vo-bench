import os
import os.path as op
import subprocess
import argparse
import glob


class RunORB2:
    def __init__(self):
        self.ORB2_ROOT = "/work/ORB_SLAM2"
        self.VOCABULARY = self.ORB2_ROOT + "/Vocabulary/ORBvoc.txt"
        self.DATA_ROOT = "/data/dataset"
        self.OUTPUT_ROOT = "/data/output"
        self.TEST_NUM = 5
        self.TEST_IDS = None

    def run_orb2(self, opt):
        self.check_base_paths()
        self.TEST_IDS = list(range(self.TEST_NUM)) if opt.test_id < 0 else [opt.test_id]

        if opt.exec == "all":
            command_makers = [self.stereo_euroc]
            commands = []
            configs = []
            for lc in [0, 1]:
                opt.loopclosing = lc
                for cmdmaker in command_makers:
                    cmds, cfgs = cmdmaker(opt)
                    commands.extend(cmds)
                    configs.extend(cfgs)
        elif opt.exec == "stereo_kitti":
            commands, configs = self.stereo_kitti(opt)
        elif opt.exec == "stereo_euroc":
            commands, configs = self.stereo_euroc(opt)
        else:
            raise FileNotFoundError()

        for ci, (cmd, cfg) in enumerate(zip(commands, configs)):
            outfile = cmd[-1]
            os.makedirs(op.dirname(outfile), exist_ok=True)
            print("\n===== RUN ORB_SLAM2 {}/{}\nconfig: {}\ncmd: {}\n"
                  .format(ci+1, len(commands), cfg, cmd))
            subprocess.run(cmd)
            subprocess.run(["chmod", "-R", "a+rw", self.OUTPUT_ROOT])
            assert op.isfile(outfile), "===== ERROR: output file was NOT created: {}".format(outfile)

    def check_base_paths(self):
        assert op.isdir(self.ORB2_ROOT), "ORB SLAM2 dir doesn't exist"
        assert op.isfile(self.VOCABULARY), "Vocabulary file doesn't exist"
        assert op.isdir(self.DATA_ROOT), "dataset dir doesn't exist"
        assert op.isdir(self.OUTPUT_ROOT), "output dir doesn't exist"

    # Usage:
    # ./Examples/Stereo/stereo_kitti Vocabulary/ORBvoc.txt \
    #       Examples/Stereo/KITTIX.yaml \
    #       PATH_TO_DATASET_FOLDER/dataset/sequences/SEQUENCE_NUMBER \
    #       loop_closing_on \
    #       output_file
    def stereo_kitti(self, opt):
        exec_path = op.join(self.ORB2_ROOT, "Examples/Stereo")
        executer = op.join(exec_path, "stereo_kitti")
        dataset = "kitti_odometry"
        dataset_path = op.join(self.DATA_ROOT, dataset, "sequences")
        outname = "orb2_vo_stereo" if opt.loopclosing == 0 else "orb2_slam_stereo"
        output_path = op.join(self.OUTPUT_ROOT, dataset)
        sequences = [s.rstrip("/") for s in glob.glob(dataset_path + "/*/")]
        sequences = [s for s in sequences if int(op.basename(s)) <= 10]
        if opt.seq_idx != -1:
            sequences = [sequences[opt.seq_idx]]

        commands = []
        configs = []
        for si, seq_path in enumerate(sequences):
            for test_id in self.TEST_IDS:
                seq_id = int(op.basename(seq_path))
                if seq_id < 3:
                    config_file = op.join(exec_path, "KITTI00-02.yaml")
                elif seq_id == 3:
                    config_file = op.join(exec_path, "KITTI03.yaml")
                elif seq_id > 3:
                    config_file = op.join(exec_path, "KITTI04-12.yaml")
                else:
                    raise FileNotFoundError()

                output_file = op.join(output_path, "{}_s{:02d}_{}.txt".format(outname, si, test_id))
                cmd = [executer, self.VOCABULARY, config_file, seq_path, str(opt.loopclosing), output_file]
                commands.append(cmd)
                conf = {"executer": outname, "loop closing": opt.loopclosing, "dataset": dataset,
                        "sequence": si, "test id": test_id}
                configs.append(conf)
            print("===== command: ", " ".join(commands[-1]))
        return commands, configs

    # Usage:
    # ./Examples/Monocular/mono_euroc Vocabulary/ORBvoc.txt \
    #       Examples/Monocular/EuRoC.yaml \
    #       PATH_TO_SEQUENCE_FOLDER/mav0/cam0/data \
    #       Examples/Monocular/EuRoC_TimeStamps/SEQUENCE.txt \
    #       loop_closing_on \
    #       path/to/output/file
    def stereo_euroc(self, opt):
        exec_path = op.join(self.ORB2_ROOT, "Examples/Stereo")
        executer = op.join(exec_path, "stereo_euroc")
        dataset = "euroc_mav"
        dataset_path = op.join(self.DATA_ROOT, dataset)
        sequences = [s + "mav0/cam0/data" for s in glob.glob(dataset_path + "/*/") if op.isdir(s+"mav0")]
        outname = "orb2_vo_stereo" if opt.loopclosing == 0 else "orb2_slam_stereo"
        output_path = op.join(self.OUTPUT_ROOT, dataset)
        if opt.seq_idx != -1:
            sequences = [sequences[opt.seq_idx]]

        config_file = op.join(exec_path, "EuRoC.yaml")
        commands = []
        configs = []
        for si, right_seq in enumerate(sequences):
            for test_id in self.TEST_IDS:
                left_seq = right_seq.replace("cam0", "cam1")
                timefile = right_seq.split("/")[-4]
                timefile = timefile.split("_")
                timefile = op.join(exec_path, "EuRoC_TimeStamps", timefile[0] + timefile[1] + ".txt")

                output_file = op.join(output_path, "{}_s{:02d}_{}.txt".format(outname, si, test_id))
                cmd = [executer, self.VOCABULARY, config_file, right_seq, left_seq, timefile,
                       str(opt.loopclosing), output_file]
                commands.append(cmd)
                conf = {"executer": outname, "loop closing": opt.loopclosing, "dataset": dataset,
                        "sequence": si, "test id": test_id}
                configs.append(conf)
            print("===== command:", " ".join(commands[-1]))
        return commands, configs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-e", "--exec", default="all", type=str, help="orbslam2 executer file, "
                        "options: all, mono_tum, mono_kitti, mono_euroc, rgbd_tum"
                        ", stereo_kitti, stereo_euroc")
    parser.add_argument("-l", "--loopclosing", default=0, type=int,
                        help="if 1, enable loop closing")
    parser.add_argument("-s", "--seq_idx", default=-1, type=int,
                        help="int: index of sequence in sequence list, -1 means all")
    parser.add_argument("-t", "--test_id", default=-1, type=int, help="test id")
    opt = parser.parse_args()
    print(opt)

    orbslam2 = RunORB2()
    orbslam2.run_orb2(opt)


if __name__ == "__main__":
    main()